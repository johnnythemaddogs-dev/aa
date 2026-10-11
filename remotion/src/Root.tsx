import {CalculateMetadataFunction, Composition, staticFile} from 'remotion';
import {alignWeights, parseWav, weight} from './align';
import {AUDIO_FILE, CUES, DEFAULT_SUNLINE, PALM_FILE, TAIL_SEC, TIMINGS_FILE} from './script';
import {TesouVideo, VideoProps} from './Video';

const FPS = 30;

const imageSize = (src: string) =>
	new Promise<[number, number]>((resolve, reject) => {
		const img = new Image();
		img.onload = () => resolve([img.naturalWidth, img.naturalHeight]);
		img.onerror = () => reject(new Error(`public/${PALM_FILE} が読み込めません`));
		img.src = src;
	});

const calculateMetadata: CalculateMetadataFunction<VideoProps> = async ({props}) => {
	const res = await fetch(staticFile(AUDIO_FILE));
	if (!res.ok) throw new Error(`public/${AUDIO_FILE} が見つかりません`);
	const wav = parseWav(await res.arrayBuffer());
	const audioSec = wav.samples.length / wav.sampleRate;

	let spans: [number, number][] | null = null;
	const tr = await fetch(staticFile(TIMINGS_FILE)).catch(() => null);
	if (tr && tr.ok) {
		const j = await tr.json().catch(() => null);
		if (Array.isArray(j) && j.length === CUES.length) spans = j;
	}
	spans ??= alignWeights(CUES.map((c) => weight(c.narration)), wav);

	const duration = audioSec + TAIL_SEC;
	// 間の無音でもテロップを途切れさせない
	const cues = spans.map(([s], i) => ({
		start: i === 0 ? 0 : s,
		end: i + 1 < spans!.length ? spans![i + 1][0] : duration,
	}));
	console.log('テロップの時間 (秒):\n' + cues.map((c, i) => `${i + 1}\t${c.start.toFixed(2)}\t${c.end.toFixed(2)}\t${CUES[i].text.replace(/\n/g, ' / ')}`).join('\n'));

	const palmSize = await imageSize(staticFile(PALM_FILE));
	return {durationInFrames: Math.ceil(duration * FPS), props: {...props, cues, palmSize}};
};

export const RemotionRoot: React.FC = () => (
	<Composition
		id="TesouTaiyousen"
		component={TesouVideo}
		width={1080}
		height={1920}
		fps={FPS}
		durationInFrames={FPS * 60}
		defaultProps={{sunline: DEFAULT_SUNLINE, cues: [], palmSize: [1024, 1536]} as VideoProps}
		calculateMetadata={calculateMetadata}
	/>
);
