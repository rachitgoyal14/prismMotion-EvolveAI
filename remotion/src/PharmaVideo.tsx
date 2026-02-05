import React from 'react';
import {AbsoluteFill, Sequence, OffthreadVideo, Img} from 'remotion';

interface Scene {
	scene_id: number;
	concept: string;
	visual_description: string;
	duration_sec: number;
	pexels_image: {
		id: number;
		src: string;
		photographer: string;
		alt: string;
	};
	pexels_video?: {
		id: number;
		src: string;
		user: string;
		duration: number;
	};
	script: string;
	image: {
		src: string;
		alt: string;
	};
	video?: {
		src: string;
	};
}

interface Props {
	scenes: Scene[];
}

const TEXT_BAR_HEIGHT = 120;

const TextOverlay: React.FC<{text: string}> = ({text}) => {
	return (
		<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', pointerEvents: 'none'}}>
			<div
				style={{
					width: '100%',
					height: TEXT_BAR_HEIGHT,
					backgroundColor: 'rgba(0, 0, 0, 0.5)',
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
					padding: '0 40px',
					textAlign: 'center',
					color: 'white',
					fontSize: 36,
					lineHeight: 1.3,
					fontWeight: 600,
					fontFamily: 'Arial, sans-serif',
				}}>
				{text}
			</div>
		</AbsoluteFill>
	);
};

export const PharmaVideo: React.FC<Props> = ({scenes}) => {
	const fps = 30;

	// Calculate cumulative from frames for each scene
	const scenesWithFrom = scenes.map((scene, index) => {
		const from = scenes
			.slice(0, index)
			.reduce((acc, s) => acc + s.duration_sec * fps, 0);
		return {...scene, from};
	});

	// Determine if any scene has video
	const hasVideo = scenes.some(scene => scene.video && scene.video.src);

	return (
		<>
			{scenesWithFrom.map(scene => {
				const {from, duration_sec, script, video, image} = scene;
				const durationFrames = duration_sec * fps;

				return (
					<Sequence key={scene.scene_id} from={from} durationInFrames={durationFrames}>
						<AbsoluteFill style={{backgroundColor: 'black', justifyContent: 'center', alignItems: 'center'}}>
							{video && video.src ? (
								<OffthreadVideo
									src={video.src}
									style={{
										width: '100%',
										height: '100%',
										objectFit: 'cover',
									}}
								/>
							) : (
								<Img
									src={image.src}
									alt={image.alt}
									style={{
										width: '100%',
										height: '100%',
										objectFit: 'cover',
									}}
								/>
							)}
							<TextOverlay text={script} />
						</AbsoluteFill>
					</Sequence>
				);
			})}

			{/* Credit frame at end */}
			<Sequence
				from={scenesWithFrom.reduce(
					(acc, scene) => acc + scene.duration_sec * fps,
					0
				)}
				durationInFrames={3 * fps}
			>
				<AbsoluteFill
					style={{
						backgroundColor: 'black',
						justifyContent: 'center',
						alignItems: 'center',
					}}
				>
					<div
						style={{
							color: 'white',
							fontSize: 48,
							fontWeight: 700,
							fontFamily: 'Arial, sans-serif',
							textAlign: 'center',
							padding: '0 40px',
						}}
					>
						{hasVideo ? 'Photos/Videos from Pexels' : 'Photos from Pexels'}
					</div>
				</AbsoluteFill>
			</Sequence>
		</>
	);
};