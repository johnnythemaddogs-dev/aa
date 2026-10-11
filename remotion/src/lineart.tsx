// 線画の部品。どの線も pathLength=1 にして、progress (0→1) で「描いていく」。
import React from 'react';

export type Pt = [number, number];

export const clamp = (x: number, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
export const prog = (t: number, start: number, dur: number) => (dur > 0 ? clamp((t - start) / dur) : t >= start ? 1 : 0);
export const easeOut = (x: number) => 1 - (1 - clamp(x)) ** 3;
export const easeInOut = (x: number) => {
	x = clamp(x);
	return x < 0.5 ? 4 * x ** 3 : 1 - (-2 * x + 2) ** 3 / 2;
};
export const easeBack = (x: number) => {
	x = clamp(x);
	const c = 1.70158;
	return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2;
};

const f = (n: number) => n.toFixed(1);
export const poly = (pts: Pt[], close = false) => 'M' + pts.map(([x, y]) => `${f(x)} ${f(y)}`).join(' L') + (close ? ' Z' : '');

export const circle = (cx: number, cy: number, r: number, startDeg = -90) => {
	const a = (startDeg * Math.PI) / 180;
	const x0 = cx + r * Math.cos(a), y0 = cy + r * Math.sin(a);
	const x1 = cx - r * Math.cos(a), y1 = cy - r * Math.sin(a);
	return `M${f(x0)} ${f(y0)} A${f(r)} ${f(r)} 0 1 1 ${f(x1)} ${f(y1)} A${f(r)} ${f(r)} 0 1 1 ${f(x0)} ${f(y0)}`;
};

export const arc = (cx: number, cy: number, r: number, startDeg: number, sweepDeg: number) => {
	const n = Math.max(12, Math.round(Math.abs(sweepDeg) / 6));
	const pts: Pt[] = [];
	for (let i = 0; i <= n; i++) {
		const a = ((startDeg + (sweepDeg * i) / n) * Math.PI) / 180;
		pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
	}
	return poly(pts);
};

export const rrect = (x0: number, y0: number, x1: number, y1: number, r: number) =>
	`M${f((x0 + x1) / 2)} ${f(y0)} H${f(x1 - r)} A${r} ${r} 0 0 1 ${f(x1)} ${f(y0 + r)} V${f(y1 - r)} A${r} ${r} 0 0 1 ${f(x1 - r)} ${f(y1)} H${f(x0 + r)} A${r} ${r} 0 0 1 ${f(x0)} ${f(y1 - r)} V${f(y0 + r)} A${r} ${r} 0 0 1 ${f(x0 + r)} ${f(y0)} Z`;

export const cubic = (p0: Pt, c1: Pt, c2: Pt, p1: Pt) => `M${f(p0[0])} ${f(p0[1])} C${f(c1[0])} ${f(c1[1])} ${f(c2[0])} ${f(c2[1])} ${f(p1[0])} ${f(p1[1])}`;

export const smooth = (points: Pt[], n = 14): Pt[] => {
	if (points.length < 3) return points;
	const p = [points[0], ...points, points[points.length - 1]];
	const out: Pt[] = [];
	for (let i = 1; i < p.length - 2; i++) {
		const [p0, p1, p2, p3] = [p[i - 1], p[i], p[i + 1], p[i + 2]];
		for (let k = 0; k < n; k++) {
			const u = k / n;
			out.push([0, 1].map(
				(j) => 0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * u + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * u * u + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * u ** 3),
			) as Pt);
		}
	}
	out.push(points[points.length - 1]);
	return out;
};

export const star5 = (cx: number, cy: number, r: number, rot = 0) => {
	const pts: Pt[] = [];
	for (let i = 0; i < 10; i++) {
		const rr = i % 2 === 0 ? r : r * 0.42;
		const a = ((-90 + rot + i * 36) * Math.PI) / 180;
		pts.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]);
	}
	return poly(pts, true);
};

export const sparkle = (cx: number, cy: number, r: number) => {
	const k = r * 0.18;
	const pts: Pt[] = [];
	for (let i = 0; i < 4; i++) {
		const a = ((i * 90 - 90) * Math.PI) / 180, b = ((i * 90 - 45) * Math.PI) / 180;
		pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)], [cx + k * Math.cos(b), cy + k * Math.sin(b)]);
	}
	return poly(pts, true);
};

export const mandala = (cx: number, cy: number, R: number, rot = 0, petals = 12) => {
	const rings = [R, R * 0.93, R * 0.58, R * 0.3].map((r) => circle(cx, cy, r, rot - 90));
	const pet: string[] = [];
	const P = (r: number, a: number): Pt => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
	for (let i = 0; i < petals; i++) {
		const a = ((rot + (i * 360) / petals - 90) * Math.PI) / 180;
		const da = (Math.PI / petals) * 0.95;
		for (const s of [-1, 1]) pet.push(cubic(P(R * 0.58, a), P(R * 0.72, a + s * da), P(R * 0.86, a + s * da * 0.5), P(R * 0.93, a)));
		const b = a + Math.PI / petals;
		for (const s of [-1, 1]) pet.push(cubic(P(R * 0.3, b), P(R * 0.45, b + s * da * 0.9), P(R * 0.45, b + s * da * 0.9), P(R * 0.55, b)));
	}
	return {rings, pet};
};

export const lotus = (cx: number, cy: number, s: number) => {
	const base: Pt = [cx, cy + 0.55 * s];
	const petals: string[] = [];
	for (const [dx, dy, w] of [[0, -0.75, 0.32], [-0.42, -0.42, 0.3], [0.42, -0.42, 0.3], [-0.82, -0.05, 0.28], [0.82, -0.05, 0.28]]) {
		const tip: Pt = [cx + dx * s, cy + dy * s];
		const ang = Math.atan2(tip[1] - base[1], tip[0] - base[0]) + Math.PI / 2;
		const nx = Math.cos(ang) * w * s, ny = Math.sin(ang) * w * s;
		const mid: Pt = [(base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2];
		for (const k of [-1, 1]) petals.push(cubic(base, [mid[0] + k * nx, mid[1] + k * ny], [tip[0] + k * nx * 0.25, tip[1] + k * ny * 0.25], tip));
	}
	const waves = [[0.68, 1], [0.8, 0.75], [0.92, 0.5]].map(([wy, ww], j) => {
		const pts: Pt[] = [];
		for (let i = 0; i <= 60; i++) {
			const u = i / 60;
			pts.push([cx - ww * s + 2 * ww * s * u, cy + wy * s + Math.sin(u * Math.PI * 4 + j) * 0.03 * s]);
		}
		return poly(pts);
	});
	return {petals, waves};
};

export const sunRays = (cx: number, cy: number, r: number, rays = 12, rot = 0) =>
	Array.from({length: rays}, (_, i) => {
		const a = ((rot + (i * 360) / rays) * Math.PI) / 180;
		const L = r * (i % 2 ? 0.75 : 0.45);
		return poly([[cx + r * 1.25 * Math.cos(a), cy + r * 1.25 * Math.sin(a)], [cx + (r * 1.25 + L) * Math.cos(a), cy + (r * 1.25 + L) * Math.sin(a)]]);
	});

export const crescent = (cx: number, cy: number, r: number) => [arc(cx, cy, r, 40, 280), arc(cx + r * 0.42, cy - r * 0.2, r * 0.82, 287, -214)];

/** 線を描く。p: 描けた割合 0→1 */
export const Draw: React.FC<{d: string; p?: number; w?: number; c?: string; o?: number; glow?: boolean; fill?: string}> = ({d, p = 1, w = 3, c = '#F4D58D', o = 1, glow = true, fill}) => {
	if (p <= 0.001 || o <= 0.003) return null;
	return (
		<path
			d={d}
			pathLength={1}
			strokeDasharray={p >= 0.999 ? undefined : '1 1'}
			strokeDashoffset={p >= 0.999 ? undefined : 1 - p}
			stroke={c}
			strokeWidth={w}
			strokeLinecap="round"
			strokeLinejoin="round"
			fill={fill ?? 'none'}
			opacity={o}
			filter={glow ? 'url(#glow)' : undefined}
		/>
	);
};

/** 複数の線を順番に (seq) または同時に描く */
export const DrawAll: React.FC<{ds: string[]; p: number; seq?: boolean} & Omit<React.ComponentProps<typeof Draw>, 'd' | 'p'>> = ({ds, p, seq = true, ...rest}) => (
	<>
		{ds.map((d, i) => (
			<Draw key={i} d={d} p={seq ? clamp(p * ds.length - i) : p} {...rest} />
		))}
	</>
);

export const GlowDefs: React.FC = () => (
	<svg width={0} height={0} style={{position: 'absolute'}}>
		<defs>
			<filter id="glow" filterUnits="userSpaceOnUse" x="0" y="0" width="1080" height="1920">
				<feGaussianBlur stdDeviation="5" result="b" />
				<feMerge>
					<feMergeNode in="b" />
					<feMergeNode in="b" />
					<feMergeNode in="SourceGraphic" />
				</feMerge>
			</filter>
			<filter id="glowBig" filterUnits="userSpaceOnUse" x="0" y="0" width="1080" height="1920">
				<feGaussianBlur stdDeviation="10" result="b" />
				<feMerge>
					<feMergeNode in="b" />
					<feMergeNode in="b" />
					<feMergeNode in="SourceGraphic" />
				</feMerge>
			</filter>
		</defs>
	</svg>
);
