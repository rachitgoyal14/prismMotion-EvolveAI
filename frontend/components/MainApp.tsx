import React, { useState, useRef, useEffect } from 'react';
import { Menu, Mic, ChevronUp, Send, Plus, Move, X, Play, RotateCw, Upload, FileText, Image as ImageIcon, Music, Film, Maximize2, Trash2, Paperclip, Download, RefreshCw, Pause } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { GoogleGenAI } from "@google/genai";

interface MainAppProps {
  userData: {
    companyName: string;
    logo?: File | null;
  };
  initialMode: 'agent' | 'creator';
}

interface Message {
  id: string;
  role: 'user' | 'ai';
  text?: string;
  videoUrl?: string;
  isLoading?: boolean;
}

interface ChatSession {
  id: string;
  title: string;
  date: Date;
}

// Node Data Interface
interface WorkflowNodeData {
  id: string;
  type: 'input' | 'user-assets' | 'scenes' | 'fetched-assets' | 'script' | 'video';
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
  isProcessing: boolean;
  isComplete: boolean;
  content: any;
}

const QUICK_ACTIONS = [
  'Clinical Ads',
  'Consumer Ads',
  'Disease awareness',
  'Mechanism of action',
  'Compliance',
  'Social media'
];

// Animation Constants
const ANIM_DURATION = 220;
const ANIM_STAGGER = 70;
const UI_SWAP_DELAY = 600;

// Fallback Key provided by user
const USER_FALLBACK_KEY = "AIzaSyCfeB7MtwyQ9ipV9mTiaPwMeJ0YfEFz35U";

const getAnimationDelay = (index: number) => `${index * ANIM_STAGGER}ms`;

// Helper to call Gemini
const generateGeminiText = async (prompt: string, model: string = 'gemini-2.5-flash'): Promise<string> => {
  try {
    const apiKey = process.env.API_KEY || USER_FALLBACK_KEY;
    if (!apiKey) throw new Error("No API Key");

    const ai = new GoogleGenAI({ apiKey: apiKey });
    const response = await ai.models.generateContent({
      model: model,
      contents: prompt,
    });
    return response.text || "No response text";
  } catch (e) {
    console.warn("Gemini API failed, using mock.", e);
    // Fallback Mock
    if (prompt.includes("scenes")) return `Scene 1: The Struggle\n[Visual: A busy office, person rubbing temples]\nNarrator: "Headaches shouldn't dictate your day."\n\nScene 2: The Relief\n[Visual: Taking the medication, smiling]\nNarrator: "Find clarity fast."`;
    if (prompt.includes("script")) return "Headaches shouldn't dictate your day. Find clarity fast with our advanced formula. Back to the moments that matter.";
    return "Generated content unavailable.";
  }
};

const MOCK_FETCHED_IMAGES = [
  "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=300&q=80",
  "https://images.unsplash.com/photo-1551076805-e1869033e561?auto=format&fit=crop&w=300&q=80",
  "https://images.unsplash.com/photo-1584036561566-b9374424e56e?auto=format&fit=crop&w=300&q=80",
  "https://images.unsplash.com/photo-1576091160550-217358c7e618?auto=format&fit=crop&w=300&q=80",
  "https://images.unsplash.com/photo-1581093458791-9f302e683837?auto=format&fit=crop&w=300&q=80",
  "https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?auto=format&fit=crop&w=300&q=80"
];

// Sub-component for Video Node content to handle player state
const VideoNodeContent = ({ url, onRegenerate }: { url: string, onRegenerate: () => void }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [showControls, setShowControls] = useState(false);

  const togglePlay = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  return (
    <div
      className="relative w-full h-full rounded-lg overflow-hidden bg-gray-100 group"
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
    >
      <video
        ref={videoRef}
        src={url}
        autoPlay
        muted
        loop
        playsInline
        className="w-full h-full object-cover"
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onClick={togglePlay}
      />

      {/* Play/Pause Overlay */}
      <div
        className={`absolute inset-0 flex items-center justify-center pointer-events-none transition-opacity duration-300 ${showControls || !isPlaying ? 'opacity-100' : 'opacity-0'}`}
      >
        <div className="bg-black/30 backdrop-blur-sm p-3 rounded-full text-white/90">
          {isPlaying ? <Pause size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" />}
        </div>
      </div>

      {/* Footer Controls */}
      <div className="absolute bottom-1 right-1 flex gap-2 pointer-events-auto z-10">
        <button
          onClick={(e) => { e.stopPropagation(); onRegenerate(); }}
          className="p-2 bg-white hover:bg-emerald-50 rounded-full text-gray-600 hover:text-emerald-600 shadow-sm border border-gray-100 transition-colors"
          title="Regenerate"
        >
          <RefreshCw size={14} />
        </button>
        <button
          className="p-2 bg-[#006838] hover:bg-[#00502b] rounded-full text-white shadow-sm transition-colors"
          title="Download"
        >
          <Download size={14} />
        </button>
      </div>
    </div>
  );
};

const MainApp: React.FC<MainAppProps> = ({ userData, initialMode }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedMode, setSelectedMode] = useState<'agent' | 'creator'>(initialMode);
  const navigate = useNavigate();

  useEffect(() => {
    setSelectedMode(initialMode);
  }, [initialMode]);

  const handleModeSwitch = (mode: 'agent' | 'creator') => {
    setSelectedMode(mode);
    navigate(`/${mode}`);
  };

  // Input & Chips State
  const [inputValue, setInputValue] = useState('');
  const [activeChip, setActiveChip] = useState<string | null>(null);

  // Chat History State
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Canvas State
  const [showCanvas, setShowCanvas] = useState(false);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [scale, setScale] = useState(1);
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0 });
  const [creatorAction, setCreatorAction] = useState<string | null>(null);

  // Workflow Nodes State
  const [nodes, setNodes] = useState<WorkflowNodeData[]>([]);
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const dragNodeOffset = useRef({ x: 0, y: 0 });

  // Execution & UI State
  const [enlargedImage, setEnlargedImage] = useState<string | null>(null);
  const [ttsState, setTtsState] = useState<'idle' | 'playing' | 'paused'>('idle');
  const ttsUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Logo
  const [logoUrl, setLogoUrl] = useState<string | null>(null);

  // Execution Status
  const isGlobalProcessing = nodes.some(n => n.isProcessing);

  useEffect(() => {
    if (userData.logo) {
      const url = URL.createObjectURL(userData.logo);
      setLogoUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [userData.logo]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (selectedMode === 'creator') {
      const timer = setTimeout(() => setShowCanvas(true), UI_SWAP_DELAY);
      return () => clearTimeout(timer);
    } else {
      setShowCanvas(false);
    }
  }, [selectedMode]);

  // --- WORKFLOW LOGIC ---

  const initializeWorkflow = (actionName: string) => {
    const formattedTitle = actionName.replace(/Ads/g, "Advertisements");
    setCreatorAction(formattedTitle);

    setPan({ x: 100, y: 100 });
    setScale(1);

    const gapX = 350;
    const baseWidth = 280;
    const baseHeight = 260;

    // Determine Final Output dimensions based on Mode
    const isSocial = actionName === 'Social media';
    // Social = Portrait (9:16 approx), Default = Landscape (16:9 approx)
    const videoNodeWidth = isSocial ? 320 : 480;
    const videoNodeHeight = isSocial ? 600 : 360;

    // Zig-Zag Layout
    const newNodes: WorkflowNodeData[] = [
      {
        id: '1', type: 'input', title: 'Context Input',
        x: 0, y: 100, width: baseWidth, height: baseHeight,
        isProcessing: false, isComplete: true,
        content: { text: '', fileName: null }
      },
      {
        id: '2', type: 'user-assets', title: 'Your Assets',
        x: gapX, y: 200, width: baseWidth, height: baseHeight,
        isProcessing: false, isComplete: true,
        content: { files: [] }
      },
      {
        id: '3', type: 'scenes', title: 'Scene Generator',
        x: gapX * 2, y: 50, width: baseWidth, height: baseHeight,
        isProcessing: false, isComplete: false,
        content: { text: '' }
      },
      {
        id: '4', type: 'fetched-assets', title: 'Fetched Assets',
        x: gapX * 3, y: 150, width: baseWidth, height: baseHeight,
        isProcessing: false, isComplete: false,
        content: { images: [] }
      },
      {
        id: '5', type: 'script', title: 'Script & TTS',
        x: gapX * 4, y: 0, width: baseWidth, height: baseHeight,
        isProcessing: false, isComplete: false,
        content: { text: '' }
      },
      {
        id: '6', type: 'video', title: 'Final Output',
        x: gapX * 5, y: 250, width: videoNodeWidth, height: videoNodeHeight,
        isProcessing: false, isComplete: false,
        content: { url: null }
      }
    ];
    setNodes(newNodes);
  };

  const handleQuickAction = (text: string) => {
    if (selectedMode === 'agent') {
      if (activeChip === text) {
        setActiveChip(null);
      } else {
        setActiveChip(text);
      }
    } else {
      initializeWorkflow(text);
    }
  };

  const handleGenerate = () => {
    if (!inputValue.trim() && !activeChip) return;
    const chipText = activeChip ? `[Selected Mode: ${activeChip}] ` : '';
    const userText = chipText + inputValue;
    const rawInput = inputValue;
    setInputValue('');
    setActiveChip(null);

    const userMsg: Message = { id: Date.now().toString(), role: 'user', text: userText };
    const loadingMsgId = (Date.now() + 1).toString();
    const loadingMsg: Message = { id: loadingMsgId, role: 'ai', isLoading: true };

    setMessages(prev => [...prev, userMsg, loadingMsg]);

    if (!currentSessionId) {
      const newId = Date.now().toString();
      let titleWords = rawInput.trim().split(/\s+/);
      let title = "";
      if (titleWords.length > 0 && titleWords[0] !== "") {
        title = titleWords.slice(0, 4).join(' ');
        if (titleWords.length > 4) title += "...";
      } else if (activeChip) {
        title = activeChip;
      } else {
        title = "New Conversation";
      }
      title = title.charAt(0).toUpperCase() + title.slice(1);

      setChatSessions(prev => [{ id: newId, title, date: new Date() }, ...prev]);
      setCurrentSessionId(newId);
    }

    setTimeout(() => {
      setMessages(prev => prev.map(msg => {
        if (msg.id === loadingMsgId) {
          return {
            ...msg,
            isLoading: false,
            videoUrl: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
          };
        }
        return msg;
      }));
    }, 4000);
  };

  const handleNewChat = () => {
    setMessages([]);
    setInputValue('');
    setActiveChip(null);
    setCurrentSessionId(null);
  };

  // --- CANVAS & NODE OPERATIONS ---

  const updateNodeContent = (id: string, newContent: any, isComplete?: boolean, isProcessing?: boolean) => {
    setNodes(prev => prev.map(n => {
      if (n.id === id) {
        return {
          ...n,
          content: { ...n.content, ...newContent },
          isComplete: isComplete !== undefined ? isComplete : n.isComplete,
          isProcessing: isProcessing !== undefined ? isProcessing : n.isProcessing
        };
      }
      return n;
    }));
  };

  const runNodeProcess = async (nodeId: string) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return;

    updateNodeContent(nodeId, {}, false, true);

    try {
      if (node.type === 'scenes') {
        const contextNode = nodes.find(n => n.type === 'input');
        const prompt = `Create 3 distinct video scenes for a pharmaceutical video ad about: "${contextNode?.content.text || "generic medication"}". 
            Output ONLY the scenes. 
            Format exactly like this for each scene:
            
            Scene [Number]: [Title]
            Visual: [Description]
            Audio: [Narration/Sound]
            `;
        const text = await generateGeminiText(prompt);
        updateNodeContent(nodeId, { text }, true, false);
      }
      else if (node.type === 'fetched-assets') {
        await new Promise(r => setTimeout(r, 1500));
        updateNodeContent(nodeId, { images: MOCK_FETCHED_IMAGES }, true, false);
      }
      else if (node.type === 'script') {
        const sceneNode = nodes.find(n => n.type === 'scenes');
        const prompt = `Based on these scenes, write a clean, ready-to-read video script narration. Do not include scene headers, just the spoken text.
            
            Scenes:
            ${sceneNode?.content.text}`;
        const text = await generateGeminiText(prompt);
        updateNodeContent(nodeId, { text }, true, false);
      }
      else if (node.type === 'video') {
        await new Promise(r => setTimeout(r, 3000));
        updateNodeContent(nodeId, { url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4' }, true, false);
      }
    } catch (e) {
      console.error(e);
      updateNodeContent(nodeId, {}, false, false);
    }
  };

  const toggleTTS = (text: string) => {
    if (!('speechSynthesis' in window)) return;

    if (ttsState === 'playing') {
      window.speechSynthesis.pause();
      setTtsState('paused');
    } else if (ttsState === 'paused') {
      window.speechSynthesis.resume();
      setTtsState('playing');
    } else {
      // Idle or new start
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onend = () => setTtsState('idle');
      ttsUtteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
      setTtsState('playing');
    }
  };

  // --- CANVAS EVENTS ---

  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (isGlobalProcessing) return; // Block interaction when processing
    if (selectedMode !== 'creator') return;
    if ((e.target as HTMLElement).closest('.workflow-node')) return;
    setIsPanning(true);
    panStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    if (selectedMode !== 'creator') return;
    if (draggedNode) {
      const deltaX = (e.clientX - dragNodeOffset.current.x) / scale;
      const deltaY = (e.clientY - dragNodeOffset.current.y) / scale;
      setNodes(prev => prev.map(n => n.id === draggedNode ? { ...n, x: deltaX, y: deltaY } : n));
      return;
    }
    if (isPanning) {
      setPan({ x: e.clientX - panStart.current.x, y: e.clientY - panStart.current.y });
    }
  };

  const handleCanvasMouseUp = () => { setIsPanning(false); setDraggedNode(null); };

  const handleWheel = (e: React.WheelEvent) => {
    if (selectedMode !== 'creator') return;
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const newScale = Math.min(Math.max(0.1, scale - e.deltaY * 0.001), 3);
      setScale(newScale);
    } else {
      setPan(prev => ({ x: prev.x - e.deltaX, y: prev.y - e.deltaY }));
    }
  };

  const startDragNode = (e: React.MouseEvent, nodeId: string, nodeX: number, nodeY: number) => {
    e.stopPropagation();
    setDraggedNode(nodeId);
    dragNodeOffset.current = { x: e.clientX - (nodeX * scale), y: e.clientY - (nodeY * scale) };
  };

  // --- RENDER NODES ---

  const renderNodeContent = (node: WorkflowNodeData) => {
    switch (node.type) {
      case 'input':
        return (
          <div className="flex flex-col h-full relative">
            <textarea
              className="flex-1 w-full bg-gray-50 border border-gray-100 rounded-xl p-3 text-sm resize-none outline-none focus:border-emerald-500 transition-colors custom-scrollbar"
              placeholder="Describe your ad requirements..."
              value={node.content.text}
              onChange={(e) => updateNodeContent(node.id, { text: e.target.value })}
              onWheel={(e) => e.stopPropagation()}
            />
            <div className="absolute bottom-3 right-3">
              <label className="cursor-pointer p-2 bg-white rounded-full shadow-sm border border-gray-200 hover:border-emerald-500 hover:text-emerald-600 transition-all flex items-center justify-center">
                <input type="file" className="hidden" onChange={(e) => {
                  if (e.target.files?.[0]) updateNodeContent(node.id, { fileName: e.target.files[0].name });
                }} />
                <Paperclip size={16} />
              </label>
            </div>
          </div>
        );
      case 'user-assets':
        return (
          <div className="flex flex-col h-full">
            {node.content.files.length > 0 ? (
              <div
                className="flex-1 overflow-y-auto custom-scrollbar p-3"
                onWheel={(e) => e.stopPropagation()}
              >
                <div className="grid grid-cols-2 gap-3">
                  {node.content.files.map((file: any, idx: number) => (
                    <div key={idx} className="aspect-square rounded-xl overflow-hidden border border-gray-100 relative bg-gray-50 group shadow-sm hover:shadow-md transition-all">
                      <img src={file.url} className="w-full h-full object-cover" alt="asset" />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          const newFiles = node.content.files.filter((_: any, i: number) => i !== idx);
                          updateNodeContent(node.id, { files: newFiles });
                        }}
                        className="absolute top-1 right-1 p-1 bg-white/90 rounded-full text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}

                  {/* Upload Button (Grid Item) */}
                  <label className="aspect-square rounded-xl border-2 border-dashed border-gray-200 flex flex-col items-center justify-center cursor-pointer hover:bg-emerald-50 hover:border-emerald-300 bg-white transition-all group">
                    <input type="file" multiple accept="image/*" className="hidden" onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                      if (e.target.files) {
                        const newFiles = Array.from(e.target.files).map((f: File) => ({ url: URL.createObjectURL(f), file: f }));
                        updateNodeContent(node.id, { files: [...node.content.files, ...newFiles] });
                      }
                    }} />
                    <Plus size={24} className="text-gray-300 group-hover:text-emerald-500 mb-1" />
                    <span className="text-[10px] font-medium text-gray-400 group-hover:text-emerald-600">Add Asset</span>
                  </label>
                </div>
              </div>
            ) : (
              <div className="flex-1 p-3 flex flex-col h-full">
                <label className="flex-1 border-2 border-dashed border-gray-200 rounded-xl flex flex-col items-center justify-center text-gray-400 hover:bg-gray-50 hover:border-emerald-300 transition-all cursor-pointer">
                  <input type="file" multiple accept="image/*" className="hidden" onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                    if (e.target.files) {
                      const newFiles = Array.from(e.target.files).map((f: File) => ({ url: URL.createObjectURL(f), file: f }));
                      updateNodeContent(node.id, { files: newFiles });
                    }
                  }} />
                  <Upload size={24} className="mb-2" />
                  <span className="text-xs">Upload Images (optional)</span>
                </label>
              </div>
            )}
          </div>
        );
      case 'scenes':
      case 'fetched-assets':
      case 'script':
        const isFetchedAssets = node.type === 'fetched-assets';
        const isScript = node.type === 'script';

        return (
          <div className="flex flex-col h-full relative">
            {!node.isComplete && !node.isProcessing && (
              <div className="flex-1 flex items-center justify-center">
                <button
                  onClick={() => runNodeProcess(node.id)}
                  className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center text-emerald-600 hover:bg-emerald-100 hover:scale-110 transition-all shadow-sm border border-emerald-100"
                >
                  <Play size={32} fill="currentColor" className="ml-1" />
                </button>
              </div>
            )}

            {node.isProcessing && (
              <div className="flex-1 flex flex-col items-center justify-center gap-3">
                <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs text-gray-500 font-medium">Generating...</span>
              </div>
            )}

            {node.isComplete && (
              <>
                {/* CONTENT AREA */}
                <div
                  className="flex-1 overflow-y-auto custom-scrollbar p-3 pb-10"
                  onWheel={(e) => e.stopPropagation()}
                >
                  {isFetchedAssets ? (
                    <div
                      className="grid grid-cols-2 gap-3"
                    >
                      {node.content.images.map((src: string, i: number) => (
                        <div key={i} className="relative group aspect-square rounded-lg overflow-hidden border border-gray-200 cursor-pointer bg-gray-100" onClick={() => setEnlargedImage(src)}>
                          <img src={src} className="w-full h-full object-cover" />
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              const newImages = node.content.images.filter((_: any, index: number) => index !== i);
                              updateNodeContent(node.id, { images: newImages });
                            }}
                            className="absolute top-1 right-1 p-1 bg-white/90 rounded-full text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <textarea
                      className="w-full h-full bg-transparent resize-none text-sm outline-none text-gray-700 font-mono leading-relaxed custom-scrollbar"
                      value={node.content.text}
                      onChange={(e) => updateNodeContent(node.id, { text: e.target.value })}
                      onWheel={(e) => e.stopPropagation()}
                    />
                  )}
                </div>

                {/* BOTTOM REGENERATE BUTTON - Fixed Bottom Right */}
                <div className="absolute bottom-1 right-1 flex gap-2">
                  {isScript && (
                    <button
                      onClick={() => toggleTTS(node.content.text)}
                      className="p-2 hover:bg-emerald-50 rounded-full text-emerald-600 bg-white shadow-sm border border-gray-100 transition-colors" title={ttsState === 'playing' ? "Pause" : "Play TTS"}
                    >
                      {ttsState === 'playing' ? <Pause size={14} fill="currentColor" /> : <Play size={14} fill="currentColor" />}
                    </button>
                  )}
                  <button
                    onClick={() => runNodeProcess(node.id)}
                    className="p-2 hover:bg-gray-100 rounded-full text-gray-600 hover:rotate-180 transition-transform duration-500 bg-white shadow-sm border border-gray-100"
                    title="Regenerate"
                  >
                    <RefreshCw size={14} />
                  </button>
                </div>
              </>
            )}
          </div>
        );
      case 'video':
        return (
          <div className="flex flex-col h-full relative bg-gray-50 p-3">
            {!node.isComplete && !node.isProcessing && (
              <div className="flex-1 flex items-center justify-center bg-black/5 rounded-lg">
                <button
                  onClick={() => runNodeProcess(node.id)}
                  className="w-20 h-20 bg-[#006838] text-white rounded-full flex items-center justify-center hover:bg-[#00502b] hover:scale-105 transition-all shadow-xl"
                >
                  <Play size={36} fill="currentColor" className="ml-1" />
                </button>
              </div>
            )}
            {node.isProcessing && (
              <div className="flex-1 flex flex-col items-center justify-center bg-black rounded-lg">
                <div className="w-10 h-10 border-2 border-white border-t-transparent rounded-full animate-spin mb-3" />
                <span className="text-white/70 text-sm">Rendering Video...</span>
              </div>
            )}
            {node.isComplete && (
              <VideoNodeContent
                url={node.content.url}
                onRegenerate={() => runNodeProcess(node.id)}
              />
            )}
          </div>
        );
    }
  };

  const renderInputBox = () => (
    <div className="w-full relative bg-white rounded-full shadow-lg border border-gray-200 focus-within:border-emerald-500 focus-within:shadow-xl transition-all duration-300 px-1 py-1 flex items-center">
      <div className="flex items-center h-full pl-1">
        <button className="p-2.5 text-gray-400 hover:text-emerald-600 transition-colors rounded-full hover:bg-gray-50 flex-shrink-0">
          <Paperclip size={20} />
        </button>
      </div>

      <div className="flex-1 flex items-center min-h-[44px] px-2 gap-2 overflow-hidden">
        {activeChip && (
          <div className="flex-shrink-0 bg-emerald-100 text-emerald-800 text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1 shadow-sm whitespace-nowrap">
            {activeChip}
            <button
              onClick={() => setActiveChip(null)}
              className="hover:text-emerald-950 p-0.5 rounded-full hover:bg-emerald-200/50 transition-colors"
            >
              <X size={12} />
            </button>
          </div>
        )}
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleGenerate();
            }
          }}
          placeholder="Ask anything or describe your video project..."
          className="flex-1 max-h-32 py-2 bg-transparent border-none outline-none text-base resize-none text-gray-800 placeholder-gray-400 custom-scrollbar self-center"
          rows={1}
          style={{ height: 'auto' }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = 'auto';
            target.style.height = `${target.scrollHeight}px`;
          }}
        />
      </div>

      <div className="flex items-center gap-1 pr-1 h-full">
        {inputValue.trim() || activeChip ? (
          <button
            onClick={handleGenerate}
            className="p-2.5 bg-emerald-600 text-white rounded-full hover:bg-emerald-700 transition-all shadow-md hover:scale-105 active:scale-95 flex-shrink-0"
          >
            <Send size={18} />
          </button>
        ) : (
          <button className="p-2.5 text-gray-400 hover:text-emerald-600 transition-colors rounded-full hover:bg-gray-50 flex-shrink-0">
            <Mic size={20} />
          </button>
        )}
      </div>
    </div>
  );

  const getActivePathEndIndex = () => {
    for (let i = nodes.length - 1; i >= 0; i--) {
      if (nodes[i].isProcessing) return i - 1;
    }
    return -1;
  };

  const activePathEndIndex = getActivePathEndIndex();

  return (
    // ROOT
    <div className="h-screen w-screen bg-[#f8fcf9] text-gray-900 font-sans overflow-hidden flex">

      {/* Sidebar */}
      <aside
        className={`bg-gray-50/80 backdrop-blur-sm flex flex-col transition-all duration-300 border-r border-gray-200 flex-shrink-0 relative z-30 overflow-x-hidden ${sidebarOpen ? 'w-72' : 'w-0 opacity-0'
          }`}
      >
        <div className="p-4 flex items-center justify-between flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(false)}
            className="p-2 hover:bg-gray-200 rounded-full text-gray-500 transition-colors"
          >
            <Menu size={20} />
          </button>
        </div>

        {/* Modes */}
        <div className="px-3 py-2 space-y-1 flex-shrink-0">
          <button
            onClick={() => handleModeSwitch('agent')}
            className={`w-full text-left px-4 py-4 rounded-lg text-lg font-medium transition-colors flex items-center gap-3 ${selectedMode === 'agent'
              ? 'bg-emerald-100 text-emerald-900'
              : 'text-gray-900 hover:bg-gray-100'
              }`}
          >
            Agent Mode
          </button>
          <button
            onClick={() => {
              handleModeSwitch('creator');
              setCreatorAction(null);
            }}
            className={`w-full text-left px-4 py-4 rounded-lg text-lg font-medium transition-colors flex items-center gap-3 ${selectedMode === 'creator'
              ? 'bg-emerald-100 text-emerald-900'
              : 'text-gray-900 hover:bg-gray-100'
              }`}
          >
            Creator Mode
          </button>
        </div>

        {/* Sidebar Content */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-6 relative no-scrollbar">
          {/* Agent Mode */}
          <div
            className={`transition-all duration-500 absolute inset-x-4 top-6 ${selectedMode === 'agent'
              ? 'opacity-100 translate-x-0 visible'
              : 'opacity-0 -translate-x-10 invisible pointer-events-none'
              }`}
          >
            <button onClick={handleNewChat} className="w-full flex items-center gap-3 px-4 py-3 mb-6 bg-white border border-gray-200 hover:border-emerald-500/50 hover:shadow-sm hover:bg-emerald-50/50 rounded-xl text-lg font-medium text-gray-700 hover:text-emerald-700 transition-all duration-200 group">
              <div className="p-1.5 bg-gray-100 rounded-lg group-hover:bg-emerald-100 transition-colors">
                <Plus size={20} className="text-gray-500 group-hover:text-emerald-600" />
              </div>
              New Chat
            </button>
            <div className="text-base font-medium text-gray-800 tracking-wide mb-4 px-2">Recent chats</div>
            {chatSessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-gray-400 text-sm">
                <p>No recent chats</p>
              </div>
            ) : (
              <div className="space-y-2">
                {chatSessions.map(chat => (
                  <button key={chat.id} onClick={() => setCurrentSessionId(chat.id)} className={`w-full text-left px-3 py-3 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-2 group ${currentSessionId === chat.id ? 'bg-gray-100' : ''}`}>
                    <span className="truncate text-gray-700 group-hover:text-gray-900 flex-1 text-base font-medium">{chat.title}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Creator Mode */}
          <div
            className={`absolute top-6 left-0 w-full px-4 flex flex-col gap-3 transition-all duration-300 ${selectedMode === 'creator' ? 'visible pointer-events-auto' : 'invisible pointer-events-none delay-[600ms]'
              }`}
          >
            <div className={`text-base font-medium text-gray-800 tracking-wide mb-2 px-1 text-left transition-opacity duration-300 ${selectedMode === 'creator' ? 'opacity-100' : 'opacity-0'}`}>
              Available modes
            </div>
            <div className="flex flex-col items-center w-full">
              <div className="flex flex-col gap-3 w-max">
                {QUICK_ACTIONS.map((action, index) => (
                  <button
                    key={action}
                    onClick={() => handleQuickAction(action)}
                    style={{
                      transitionDelay: getAnimationDelay(index),
                      transitionDuration: `${ANIM_DURATION}ms`,
                      transitionProperty: 'all',
                      transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)',
                    }}
                    className={`
                            w-full px-5 py-3 bg-[#006838] hover:bg-[#00502b] text-white rounded-full font-medium shadow-md text-sm whitespace-nowrap
                            ${selectedMode === 'creator'
                        ? 'opacity-100 translate-x-0 scale-100'
                        : 'opacity-0 translate-x-[150%] scale-90'
                      }
                        `}
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* User Info */}
        <div className="p-4 border-t border-gray-200 flex-shrink-0 bg-white/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold text-xs shadow-sm">
              {userData.companyName ? userData.companyName.charAt(0).toUpperCase() : 'U'}
            </div>
            <span className="text-sm font-semibold text-gray-700 truncate">{userData.companyName}</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative h-full min-w-0 overflow-hidden">

        {/* Top Header */}
        <header className="absolute top-0 left-0 w-full flex items-center justify-between px-8 py-5 z-40 bg-transparent pointer-events-none">
          <div className="flex items-center gap-4 pointer-events-auto">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 hover:bg-gray-100 rounded-full text-gray-600 bg-white/80 backdrop-blur-sm shadow-sm"
              >
                <Menu size={20} />
              </button>
            )}
            <span className="text-xl font-black tracking-tighter text-black select-none">
              PRISM <span className="text-emerald-600">MOTION</span>
            </span>
          </div>
          <div className="relative pointer-events-auto">
            {logoUrl ? (
              <img src={logoUrl} alt="Company Logo" className="w-10 h-10 rounded-full object-cover border border-gray-200 shadow-sm" />
            ) : (
              <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 font-bold border border-gray-300">
                {userData.companyName ? userData.companyName.charAt(0).toUpperCase() : 'U'}
              </div>
            )}
          </div>
        </header>

        {/* CONTENT LAYER */}
        <div className="relative w-full h-full overflow-hidden">

          {/* AGENT MODE: WORKSPACE */}
          <div
            className={`absolute inset-0 flex flex-col transition-opacity duration-300 ease-in-out z-10 ${selectedMode === 'agent' ? 'opacity-100 visible delay-0' : 'opacity-0 invisible delay-[600ms]'
              }`}
          >
            {/* Agent UI Content (Same as before) */}
            <div className="absolute inset-0 z-0 pointer-events-none" style={{ backgroundImage: 'radial-gradient(rgba(16, 160, 120, 0.22) 2px, transparent 2px)', backgroundSize: '24px 24px', opacity: 1 }} />
            <div className="absolute inset-0 z-0 pointer-events-none bg-[radial-gradient(circle_at_center,rgba(16,160,120,0.05)_0%,rgba(248,252,249,1)_80%)]" />

            {messages.length === 0 && (
              <div className="flex-1 flex flex-col items-center justify-center w-full min-h-0 z-10">
                <div className="text-center space-y-4 mb-10 px-4 max-w-4xl mx-auto flex-shrink-0">
                  <h1 className="text-5xl md:text-6xl font-medium text-transparent bg-clip-text bg-gradient-to-r from-emerald-700 to-teal-600 tracking-tight leading-tight">
                    Hello, {userData.companyName || 'Traveler'}
                  </h1>
                  <h2 className="text-3xl md:text-4xl font-medium text-gray-400">
                    How can I help you today?
                  </h2>
                </div>
                <div className="w-full flex flex-col items-center gap-8 flex-shrink-0">
                  <div className="w-full max-w-5xl px-6">
                    {renderInputBox()}
                  </div>
                  <div className="w-full max-w-6xl px-6 flex justify-center">
                    <div className="flex flex-nowrap gap-3 overflow-x-auto no-scrollbar py-2 w-full justify-center">
                      {QUICK_ACTIONS.map((action, index) => (
                        <button
                          key={action}
                          onClick={() => handleQuickAction(action)}
                          style={{ transitionDelay: getAnimationDelay(index), transitionDuration: `${ANIM_DURATION}ms`, transitionProperty: 'all', transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)', }}
                          className={`flex-shrink-0 px-5 py-2.5 bg-[#006838] hover:bg-[#00502b] text-white rounded-full font-medium shadow-sm text-sm md:text-base whitespace-nowrap hover:-translate-y-0.5 w-max ${selectedMode === 'agent' ? 'opacity-100 translate-x-0 scale-100' : 'opacity-0 -translate-x-[150%] scale-90'}`}
                        >
                          {action}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
            {/* Active Chat */}
            {messages.length > 0 && (
              <div className="flex-1 flex flex-col w-full max-w-5xl mx-auto h-full z-10 pt-20 pb-4 px-4 overflow-hidden">
                <div className="flex-1 overflow-y-auto pr-2 pb-4 space-y-6 custom-scrollbar">
                  {messages.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      {msg.role === 'ai' && (
                        <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center mr-3 mt-1 flex-shrink-0 text-emerald-700">
                          <div className="text-xs font-bold">AI</div>
                        </div>
                      )}
                      <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${msg.role === 'user'
                        ? 'bg-[#006838] text-white rounded-tr-none'
                        : 'bg-white border border-gray-100 shadow-sm text-gray-800 rounded-tl-none'
                        }`}>
                        {msg.text && <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>}
                        {msg.isLoading && (
                          <div className="flex gap-1 items-center h-6">
                            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                        )}
                        {msg.videoUrl && (
                          <div className="mt-3 rounded-xl overflow-hidden bg-black aspect-video relative group cursor-pointer border border-gray-200">
                            <video src={msg.videoUrl} controls className="w-full h-full object-cover" />
                          </div>
                        )}
                      </div>
                      {msg.role === 'user' && (
                        <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center ml-3 mt-1 flex-shrink-0 text-white font-bold text-xs">
                          {userData.companyName ? userData.companyName.charAt(0).toUpperCase() : 'U'}
                        </div>
                      )}
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
                <div className="pt-4 flex flex-col gap-4">
                  {renderInputBox()}
                  <div className="w-full flex justify-center">
                    <div className="flex flex-nowrap gap-3 overflow-x-auto no-scrollbar py-2 w-full justify-center">
                      {QUICK_ACTIONS.map((action, index) => (
                        <button
                          key={action}
                          onClick={() => handleQuickAction(action)}
                          style={{ transitionDelay: getAnimationDelay(index), transitionDuration: `${ANIM_DURATION}ms`, transitionProperty: 'all', transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)', }}
                          className={`flex-shrink-0 px-5 py-2.5 bg-[#006838] hover:bg-[#00502b] text-white rounded-full font-medium shadow-sm text-sm md:text-base whitespace-nowrap hover:-translate-y-0.5 w-max ${selectedMode === 'agent' ? 'opacity-100 translate-x-0 scale-100' : 'opacity-0 -translate-x-[150%] scale-90'}`}
                        >
                          {action}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* CREATOR MODE: INFINITE CANVAS */}
          <div
            className={`absolute inset-0 z-0 bg-white transition-opacity duration-300 ease-in-out ${showCanvas ? 'opacity-100 visible' : 'opacity-0 invisible'
              }`}
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleCanvasMouseMove}
            onMouseUp={handleCanvasMouseUp}
            onMouseLeave={handleCanvasMouseUp}
            onWheel={handleWheel}
            style={{ cursor: isPanning ? 'grabbing' : 'default' }}
          >
            {/* Dot Grid with Dimming Effect */}
            <div
              className="absolute inset-0 w-full h-full pointer-events-none transition-opacity duration-300"
              style={{
                backgroundColor: 'white',
                backgroundImage: 'radial-gradient(rgba(16, 160, 120, 0.55) 2px, transparent 2px)',
                backgroundSize: `${30 * scale}px ${30 * scale}px`,
                backgroundPosition: `${pan.x}px ${pan.y}px`,
                opacity: isGlobalProcessing ? 0.5 : 1,
                maskImage: 'radial-gradient(circle at center, black 30%, rgba(0,0,0,0.2) 100%)',
                WebkitMaskImage: 'radial-gradient(circle at center, black 30%, rgba(0,0,0,0.2) 100%)'
              }}
            />

            {/* Modal for Images */}
            {enlargedImage && (
              <div className="fixed inset-0 z-[100] bg-black/80 flex items-center justify-center p-10 cursor-pointer" onClick={() => setEnlargedImage(null)}>
                <img src={enlargedImage} className="max-w-full max-h-full rounded-lg shadow-2xl" alt="Enlarged" />
              </div>
            )}

            {/* CANVAS CONTENT CONTAINER */}
            <div
              className="absolute top-0 left-0 w-full h-full origin-top-left"
              style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})` }}
            >
              {/* Dynamic Title moving with canvas */}
              {creatorAction && (
                <div className={`absolute -top-24 left-1/2 -translate-x-1/2 min-w-[300px] bg-white/90 backdrop-blur-md px-8 py-4 rounded-full shadow-lg border border-emerald-100 z-0 text-center transition-opacity duration-300 ${isGlobalProcessing ? 'opacity-50' : 'opacity-100'}`}>
                  <h2 className="text-2xl font-bold text-emerald-900 whitespace-nowrap">{creatorAction}</h2>
                </div>
              )}

              {/* CONNECTIONS (CURVED) */}
              {creatorAction && (
                <svg className="absolute top-0 left-0 w-[5000px] h-[5000px] pointer-events-none overflow-visible z-0">
                  <defs>
                    <linearGradient id="neonGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
                      <stop offset="100%" stopColor="#34d399" stopOpacity="0.8" />
                    </linearGradient>
                  </defs>
                  {nodes.slice(0, -1).map((node, i) => {
                    const nextNode = nodes[i + 1];
                    const startX = node.x + node.width;
                    const startY = node.y + node.height / 2;
                    const endX = nextNode.x;
                    const endY = nextNode.y + nextNode.height / 2;

                    // Curvature logic for S-shape
                    const controlPoint1X = startX + (endX - startX) * 0.5;
                    const controlPoint1Y = startY;
                    const controlPoint2X = endX - (endX - startX) * 0.5;
                    const controlPoint2Y = endY;

                    // Neon Flow Logic: 
                    // Glowing path should extend from the start to the node currently processing (or complete)
                    const isPathActive = i <= activePathEndIndex;

                    return (
                      <g key={`conn-${i}`}>
                        <path
                          d={`M ${startX} ${startY} C ${controlPoint1X} ${controlPoint1Y}, ${controlPoint2X} ${controlPoint2Y}, ${endX} ${endY}`}
                          fill="none"
                          stroke="#e5e7eb"
                          strokeWidth="3"
                        />
                        <path
                          d={`M ${startX} ${startY} C ${controlPoint1X} ${controlPoint1Y}, ${controlPoint2X} ${controlPoint2Y}, ${endX} ${endY}`}
                          fill="none"
                          stroke={isPathActive ? "url(#neonGradient)" : "#10b981"}
                          strokeWidth={isPathActive ? "4" : "0"}
                          className={isPathActive ? "animate-[dash_1s_linear_infinite]" : "opacity-0"}
                          strokeDasharray="10, 10"
                          style={{ filter: 'drop-shadow(0 0 6px rgba(16, 185, 129, 0.8))' }}
                        />
                      </g>
                    );
                  })}
                </svg>
              )}

              {/* NODES - Interactive Lock Applied Here */}
              <div className={isGlobalProcessing ? 'pointer-events-none' : ''}>
                {creatorAction && nodes.map((node) => (
                  <div
                    key={node.id}
                    className={`workflow-node absolute bg-white rounded-2xl border-2 border-emerald-500/20 shadow-xl flex flex-col overflow-hidden transition-all duration-300 hover:border-emerald-500/50 hover:shadow-2xl z-10`}
                    style={{
                      left: node.x,
                      top: node.y,
                      width: node.width,
                      height: node.height,
                    }}
                  >
                    {/* Header */}
                    <div
                      className="bg-emerald-50/50 border-b border-emerald-100 px-4 py-2 cursor-grab active:cursor-grabbing flex justify-between items-center select-none"
                      onMouseDown={(e) => startDragNode(e, node.id, node.x, node.y)}
                    >
                      <div className="flex items-center gap-2 text-emerald-900 font-bold text-xs uppercase tracking-wider">
                        {node.type === 'input' && <FileText size={14} />}
                        {node.type === 'user-assets' && <Upload size={14} />}
                        {node.type === 'scenes' && <Film size={14} />}
                        {node.type === 'fetched-assets' && <ImageIcon size={14} />}
                        {node.type === 'script' && <Music size={14} />}
                        {node.type === 'video' && <Play size={14} />}
                        {node.title}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 p-3 overflow-hidden relative">
                      {renderNodeContent(node)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Fallback Empty State */}
            {!creatorAction && (
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none select-none text-center">
                <div className="w-[400px] h-[240px] border-2 border-dashed border-emerald-300/50 bg-emerald-50/20 rounded-[32px] flex flex-col items-center justify-center backdrop-blur-[1px] mb-4">
                  <span className="text-emerald-500 font-bold text-2xl tracking-tight">Select a Workflow</span>
                </div>
              </div>
            )}

            <style>{`
                    @keyframes dash {
                        to {
                            stroke-dashoffset: -40;
                        }
                    }
                    .custom-scrollbar::-webkit-scrollbar {
                        width: 0px; /* Chrome/Safari */
                        display: none;
                    }
                    .custom-scrollbar {
                        -ms-overflow-style: none;  /* IE/Edge */
                        scrollbar-width: none;  /* Firefox */
                    }
                `}</style>
          </div>
        </div>
      </main>
    </div>
  );
};

export default MainApp;