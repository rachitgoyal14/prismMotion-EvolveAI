import React from 'react';
import {AbsoluteFill, Sequence, OffthreadVideo, Img, useVideoConfig} from 'remotion';

interface Scene {
	scene_id: number;
	concept: string;
	duration_sec: number;
	image: {
		src: string;
		alt: string;
	};
	video?: {
		src: string;
	};
	script: string;
}

interface Props {
	scenes: Scene[];
}

const TEXT_BAR_HEIGHT = 120;

const TextOverlay: React.FC<{text: string}> = ({text}) => {
	return (
		<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 40}}>
			<div
				style={{
					backgroundColor: 'rgba(0, 0, 0, 0.5)',
					width: '100%',
					height: TEXT_BAR_HEIGHT,
					display: 'flex',
					justifyContent: 'center',
					alignItems: 'center',
					padding: '0 40px',
					boxSizing: 'border-box',
				}}
			>
				<p
					style={{
						color: 'white',
						fontSize: 36,
						textAlign: 'center',
						lineHeight: 1.3,
						fontWeight: 600,
						textShadow: '0 0 8px rgba(0,0,0,0.8)',
						margin: 0,
					}}
				>
					{text}
				</p>
			</div>
		</AbsoluteFill>
	);
};

export const PharmaVideo: React.FC<Props> = ({scenes}) => {
	const {fps, width, height} = useVideoConfig();

	// Calculate cumulative frames for each scene
	const scenesWithFrom = scenes.map((scene, index) => {
		const from = scenes
			.slice(0, index)
			.reduce((acc, s) => acc + s.duration_sec * fps, 0);
		return {...scene, from};
	});

	// Determine if any scene has video
	const hasVideo = scenes.some((scene) => scene.video && scene.video.src);

	// Total duration in frames
	const totalFrames = scenesWithFrom.reduce(
		(acc, scene) => Math.max(acc, scene.from + scene.duration_sec * fps),
		0
	) + (3 * fps); // +3 seconds for credits

	return (
		<>
			{scenesWithFrom.map((scene) => {
				const durationFrames = scene.duration_sec * fps;
				return (
					<Sequence key={scene.scene_id} from={scene.from} durationInFrames={durationFrames}>
						<AbsoluteFill style={{backgroundColor: 'black'}}>
							{scene.video && scene.video.src ? (
								<OffthreadVideo
									src={scene.video.src}
									style={{
										width: '100%',
										height: '100%',
										objectFit: 'cover',
									}}
									playbackRate={1}
								/>
							) : (
								<Img
									src={scene.image.src}
									alt={scene.image.alt}
									style={{
										width: '100%',
										height: '100%',
										objectFit: 'cover',
									}}
								/>
							)}
							<TextOverlay text={scene.script} />
						</AbsoluteFill>
					</Sequence>
				);
			})}

			{/* Credits sequence */}
			<Sequence from={totalFrames - 3 * fps} durationInFrames={3 * fps}>
				<AbsoluteFill
					style={{
						backgroundColor: 'black',
						justifyContent: 'center',
						alignItems: 'center',
						display: 'flex',
					}}
				>
					<p
						style={{
							color: 'white',
							fontSize: 48,
							fontWeight: 'bold',
							textAlign: 'center',
							textShadow: '0 0 10px rgba(0,0,0,0.9)',
							margin: 0,
						}}
					>
						{hasVideo ? 'Photos/Videos from Pexels' : 'Photos from Pexels'}
					</p>
				</AbsoluteFill>
			</Sequence>
		</>
	);
};