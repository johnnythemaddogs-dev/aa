// app/subtitles.py と同じ考え方: 音声の無音区間を探し、読みの長さの比率に近い無音でテロップを切り替える。

const PAUSE: Record<string, number> = {'。': 3, '！': 3, '？': 3, '!': 3, '?': 3, '、': 1.5, '，': 1.5, ',': 1.5, '…': 2};

export const weight = (raw: string): number => {
	let w = 0;
	for (const ch of raw) {
		if (ch in PAUSE) w += PAUSE[ch];
		else if (/\s/.test(ch) || '「」『』（）()【】'.includes(ch)) continue;
		else if (ch >= '一' && ch <= '鿿') w += 2.2;
		else if (/[A-Za-z0-9]/.test(ch)) w += 1.5;
		else w += 1;
	}
	return Math.max(w, 0.5);
};

export type Wav = {samples: Float32Array; sampleRate: number};

export const parseWav = (buf: ArrayBuffer): Wav => {
	const v = new DataView(buf);
	const tag = (o: number) => String.fromCharCode(v.getUint8(o), v.getUint8(o + 1), v.getUint8(o + 2), v.getUint8(o + 3));
	if (tag(0) !== 'RIFF' || tag(8) !== 'WAVE') throw new Error('WAV ファイルではありません');
	let pos = 12;
	let fmt = 1, ch = 1, sr = 44100, bits = 16;
	while (pos + 8 <= v.byteLength) {
		const id = tag(pos);
		const size = v.getUint32(pos + 4, true);
		const body = pos + 8;
		if (id === 'fmt ') {
			fmt = v.getUint16(body, true);
			ch = v.getUint16(body + 2, true);
			sr = v.getUint32(body + 4, true);
			bits = v.getUint16(body + 14, true);
			if (fmt === 0xfffe) fmt = v.getUint16(body + 24, true);
		} else if (id === 'data') {
			const bytes = bits / 8;
			const n = Math.floor(Math.min(size, v.byteLength - body) / (bytes * ch));
			const out = new Float32Array(n);
			for (let i = 0; i < n; i++) {
				let s = 0;
				for (let c = 0; c < ch; c++) {
					const o = body + (i * ch + c) * bytes;
					if (fmt === 3) s += bits === 64 ? v.getFloat64(o, true) : v.getFloat32(o, true);
					else if (bits === 16) s += v.getInt16(o, true) / 32768;
					else if (bits === 24) s += ((v.getUint8(o) | (v.getUint8(o + 1) << 8) | (v.getInt8(o + 2) << 16)) / 8388608);
					else if (bits === 32) s += v.getInt32(o, true) / 2147483648;
					else s += (v.getUint8(o) - 128) / 128;
				}
				out[i] = s / ch;
			}
			return {samples: out, sampleRate: sr};
		}
		pos = body + size + (size % 2);
	}
	throw new Error('WAV に音声データがありません');
};

const analyze = ({samples: y, sampleRate: sr}: Wav) => {
	const dur = y.length / sr;
	const hop = Math.max(1, Math.round(sr * 0.01));
	const n = Math.floor(y.length / hop);
	const rms = new Float32Array(n);
	let peak = 0;
	for (let i = 0; i < n; i++) {
		let s = 0;
		for (let k = i * hop; k < (i + 1) * hop; k++) s += y[k] * y[k];
		rms[i] = Math.sqrt(s / hop);
		peak = Math.max(peak, rms[i]);
	}
	if (n < 2 || peak <= 1e-6) return {start: 0, end: dur, silences: [] as [number, number][]};
	const th = peak * 10 ** (-38 / 20);
	let start = 0, end = dur;
	const silences: [number, number][] = [];
	for (let i = 0; i < n; ) {
		if (rms[i] < th) {
			let j = i;
			while (j < n && rms[j] < th) j++;
			if (i === 0) start = j * 0.01;
			else if (j === n) end = i * 0.01;
			else if (j - i >= 8) silences.push([i * 0.01, j * 0.01]);
			i = j;
		} else i++;
	}
	return end > start ? {start, end, silences} : {start: 0, end: dur, silences: []};
};

export const alignWeights = (weights: number[], wav: Wav): [number, number][] => {
	const {start, end, silences} = analyze(wav);
	const total = weights.reduce((a, b) => a + b, 0);
	const mids = silences.map(([s, e]) => (s + e) / 2);
	const used = new Set<number>();
	const bounds = [start];
	const span = end - start;
	let cum = 0;
	for (const w of weights.slice(0, -1)) {
		cum += w;
		const target = start + (span * cum) / total;
		const win = Math.min(0.7, (0.45 * span * w) / total + 0.25);
		let best: [number, number, number] | null = null;
		mids.forEach((m, idx) => {
			if (used.has(idx) || m <= bounds[bounds.length - 1] + 0.15 || m >= end - 0.15) return;
			const d = Math.abs(m - target);
			if (d <= win && (!best || d < best[0])) best = [d, idx, m];
		});
		if (best) {
			used.add(best[1]);
			bounds.push(best[2]);
		} else bounds.push(Math.max(target, bounds[bounds.length - 1] + 0.15));
	}
	bounds.push(end);
	return weights.map((_, i) => [bounds[i], Math.max(bounds[i + 1], bounds[i] + 0.1)]);
};
