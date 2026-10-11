import React from 'react';
import {AbsoluteFill, Audio, Img, random, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont as loadMaru} from '@remotion/google-fonts/ZenMaruGothic';
import {loadFont as loadMincho} from '@remotion/google-fonts/ShipporiMincho';
import {loadFont as loadUD} from '@remotion/google-fonts/BIZUDPGothic';
import {
	Draw, DrawAll, GlowDefs, Pt, circle, clamp, crescent, easeBack, easeInOut, easeOut, lotus, mandala, poly, prog, rrect, smooth, sparkle,
	star5, sunRays,
} from './lineart';
import {AUDIO_FILE, CUES, PALM_FILE, SCENE_AT, TITLE} from './script';

const fontOpts = {weights: ['700' as const], subsets: ['japanese' as const, 'latin' as const], ignoreTooManyRequestsWarning: true};
const MARU = loadMaru('normal', fontOpts).fontFamily;
const MINCHO = loadMincho('normal', fontOpts).fontFamily;
const UD = loadUD('normal', {weights: ['400', '700'], subsets: ['japanese', 'latin'], ignoreTooManyRequestsWarning: true}).fontFamily;

export type VideoProps = {
	sunline: Pt[];
	cues: {start: number; end: number}[];
	palmSize: [number, number];
};

const C = {gold: '#F4D58D', ivory: '#FFF4DC', sun: '#FFB443', ink: '#1B0F33'};
const TELOP_Y = 1430;
const PALM_C: Pt = [540, 800];
const PALM_BOX: Pt = [880, 980];
const XFADE = 0.45;

type Ctx = VideoProps & {t: number; cs: (i: number) => number; palmRect: [number, number, number, number]; sun: Pt[]};
type Scene = (ctx: Ctx, a: number) => React.ReactNode;

const Svg: React.FC<{children: React.ReactNode; o?: number}> = ({children, o = 1}) => (
	<svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0, opacity: o}}>
		{children}
	</svg>
);

const Glow: React.FC<{x: number; y: number; r: number; color: string; o: number}> = ({x, y, r, color, o}) =>
	o <= 0.003 ? null : (
		<div style={{position: 'absolute', left: x - r, top: y - r, width: r * 2, height: r * 2, borderRadius: '50%', opacity: o,
			background: `radial-gradient(circle, ${color} 0%, transparent 70%)`}} />
	);

// ================================================================ telop

const emWidth = (s: string) => [...s.replace(/[[\]]/g, '')].reduce((w, ch) => w + (/[\x20-\x7e]/.test(ch) ? 0.56 : 1.04), 0);

const Marked: React.FC<{line: string}> = ({line}) => (
	<>
		{line.split(/(\[[^\]]+\])/).filter(Boolean).map((seg, i) =>
			seg.startsWith('[') ? <span key={i} style={{color: '#FFD976'}}>{seg.slice(1, -1)}</span> : <span key={i}>{seg}</span>,
		)}
	</>
);

const Telop: React.FC<{text: string; k: number}> = ({text, k}) => {
	const lines = text.split('\n');
	const size = Math.min(76, 930 / Math.max(...lines.map(emWidth)));
	return (
		<div style={{position: 'absolute', left: 0, right: 0, top: TELOP_Y, display: 'flex', justifyContent: 'center',
			transform: `translateY(calc(-50% + ${18 * (1 - k)}px))`, opacity: k}}>
			<div style={{background: 'rgba(22,13,46,0.66)', borderRadius: 36, padding: '22px 40px', fontFamily: MARU, fontWeight: 700,
				fontSize: size, lineHeight: 1.36, color: 'white', textAlign: 'center', whiteSpace: 'nowrap', letterSpacing: '0.04em',
				WebkitTextStroke: `${Math.round(size / 11)}px ${C.ink}`, paintOrder: 'stroke fill',
				textShadow: '0 4px 14px rgba(0,0,0,0.45)'}}>
				{lines.map((ln, i) => <div key={i}><Marked line={ln} /></div>)}
			</div>
		</div>
	);
};

// ================================================================ background

const Background: React.FC<{t: number}> = ({t}) => {
	const {rings, pet} = mandala(540, 800, 500, t * 2, 16);
	const k = easeInOut(prog(t, 0, 3));
	return (
		<AbsoluteFill style={{background: 'linear-gradient(180deg, #130E36 0%, #251645 55%, #33205A 100%)'}}>
			<Glow x={540} y={820} r={620} color="rgba(138,92,200,0.35)" o={1} />
			<Svg>
				{Array.from({length: 90}, (_, i) => {
					const tw = 0.5 + 0.5 * Math.sin(t * (0.6 + random(`sp${i}`)) + random(`ph${i}`) * 6.28);
					return <circle key={i} cx={20 + random(`x${i}`) * 1040} cy={20 + random(`y${i}`) * 1880} r={(1.2 + random(`r${i}`) * 2) * (0.6 + 0.4 * tw)}
						fill={C.gold} opacity={0.25 + 0.6 * tw} />;
				})}
				<DrawAll ds={rings} p={k} seq={false} w={2} o={0.16} glow={false} />
				<DrawAll ds={pet} p={k} seq={false} w={1.6} o={0.12} glow={false} />
			</Svg>
		</AbsoluteFill>
	);
};

const Title: React.FC<{t: number}> = ({t}) => {
	const ta = easeOut(prog(t, 0.2, 0.8));
	return (
		<>
			<div style={{position: 'absolute', top: 168 - 12 * (1 - ta), left: 0, right: 0, textAlign: 'center', opacity: ta, fontFamily: MINCHO,
				fontWeight: 700, fontSize: 52, color: '#FFE9B0', letterSpacing: '0.04em', textShadow: '0 0 18px rgba(255,200,120,0.45)'}}>
				{TITLE}
			</div>
			<Svg>
				<Draw d={poly([[90, 262], [990, 262]])} p={easeInOut(prog(t, 0.5, 1.2))} w={2} />
				<Draw d={star5(64, 208, 12)} p={prog(t, 1.2, 0.4)} w={2} />
				<Draw d={star5(1016, 208, 12)} p={prog(t, 1.2, 0.4)} w={2} />
			</Svg>
		</>
	);
};

// ================================================================ scenes

const Avatar: React.FC<{size?: number}> = ({size = 92}) => (
	<svg width={size} height={size} viewBox="0 0 92 92">
		<circle cx={46} cy={46} r={46} fill="#E9D8F2" />
		<circle cx={46} cy={32} r={16} fill="#A88CC0" />
		<path d="M14 84 A32 32 0 0 1 78 84 Z" fill="#A88CC0" />
	</svg>
);

const Bubble: React.FC<{children: React.ReactNode; side: 'l' | 'r'; s: number}> = ({children, side, s}) => (
	<div style={{position: 'relative', background: side === 'l' ? 'white' : '#8DE063', color: '#222', borderRadius: 34, padding: '20px 32px',
		fontFamily: UD, fontSize: 40, lineHeight: 1.4, whiteSpace: 'nowrap', transform: `scale(${s})`,
		transformOrigin: side === 'l' ? 'top left' : 'top right'}}>
		<div style={{position: 'absolute', top: 8, [side === 'l' ? 'left' : 'right']: -12, width: 0, height: 0, borderTop: '12px solid transparent',
			borderBottom: '12px solid transparent', [side === 'l' ? 'borderRight' : 'borderLeft']: `22px solid ${side === 'l' ? 'white' : '#8DE063'}`}} />
		{children}
	</div>
);

const sceneChat: Scene = (ctx, a) => {
	const {t} = ctx;
	const e = easeBack(prog(t, 0, 0.7));
	const c1 = ctx.cs(1), c2 = ctx.cs(2);
	const typing = prog(t, 0.8, 0.25);
	return (
		<AbsoluteFill style={{opacity: a * prog(t, 0, 0.4)}}>
			<div style={{position: 'absolute', left: 90, top: 300, width: 900, height: 940, borderRadius: 44, overflow: 'hidden', background: '#8FA6CF',
				transform: `scale(${0.9 + 0.1 * e})`, boxShadow: '0 20px 60px rgba(0,0,0,0.45)', fontFamily: UD}}>
				<div style={{height: 130, background: '#273250', color: 'white', fontSize: 40, fontWeight: 700, display: 'flex', alignItems: 'center',
					justifyContent: 'center', position: 'relative'}}>
					<svg width={40} height={60} style={{position: 'absolute', left: 36}}><path d="M28 10 L10 30 L28 50" stroke="white" strokeWidth={6} fill="none" strokeLinecap="round" /></svg>
					公式LINE　手相の無料鑑定
				</div>
				<div style={{display: 'flex', justifyContent: 'center', marginTop: 30}}>
					<div style={{background: 'rgba(60,75,110,0.45)', color: 'white', fontSize: 28, padding: '6px 22px', borderRadius: 23}}>今日</div>
				</div>
				<div style={{position: 'absolute', left: 28, top: 250, display: 'flex', gap: 14, opacity: t < c1 ? typing : 1}}>
					<Avatar />
					<div>
						<div style={{fontSize: 28, color: '#F5F7FF', marginBottom: 8, opacity: t >= c1 ? 1 : 0}}>ご相談者さま</div>
						<div style={{display: 'flex', alignItems: 'flex-end', gap: 10}}>
							{t < c1 ? (
								<Bubble side="l" s={1}>
									<div style={{display: 'flex', gap: 14, height: 56, alignItems: 'center'}}>
										{[0, 1, 2].map((i) => {
											const ph = (t * 3 - i * 0.33) % 1;
											const r = 8 + 4 * Math.max(0, Math.sin(ph * Math.PI));
											return <div key={i} style={{width: r * 2, height: r * 2, borderRadius: '50%', background: '#9696A0'}} />;
										})}
									</div>
								</Bubble>
							) : (
								<>
									<Bubble side="l" s={easeBack(prog(t, c1, 0.4))}>両手に太陽線があるのに、<br />全然お金も人気もありません…</Bubble>
									<div style={{fontSize: 24, color: '#EEF2FA', opacity: prog(t, c1 + 0.3, 0.3)}}>23:03</div>
								</>
							)}
						</div>
					</div>
				</div>
				{t >= c2 + 0.2 && (
					<div style={{position: 'absolute', right: 30, top: 560, display: 'flex', alignItems: 'flex-end', gap: 10}}>
						<div style={{fontSize: 24, color: '#EEF2FA', textAlign: 'right', opacity: prog(t, c2 + 0.6, 0.3)}}>既読<br />23:05</div>
						<Bubble side="r" s={easeBack(prog(t, c2 + 0.2, 0.4))}>ご相談ありがとうございます<br />実は、よくあるお悩みなんです</Bubble>
					</div>
				)}
				<div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 120, background: '#F3F4F7', display: 'flex', alignItems: 'center', gap: 20, padding: '0 34px'}}>
					<div style={{width: 44, height: 44, borderRadius: '50%', border: '4px solid #9AA0AA'}} />
					<div style={{flex: 1, height: 66, borderRadius: 33, background: 'white', border: '2px solid #D5D8DE', color: '#A0A4AC', fontSize: 32,
						display: 'flex', alignItems: 'center', paddingLeft: 30}}>メッセージを入力</div>
					<div style={{width: 44, height: 44, borderRadius: '50%', border: '4px solid #9AA0AA'}} />
				</div>
			</div>
			<Svg>
				{[[120, 285, 26], [975, 420, 20], [985, 1200, 30], [95, 1050, 18]].map(([x, y, r], i) => {
					const tw = 0.5 + 0.5 * Math.sin(t * 2.2 + i * 1.7);
					return <Draw key={i} d={sparkle(x, y, r * (0.7 + 0.3 * tw))} p={prog(t, 0.6 + i * 0.2, 0.5)} w={2.5} c={C.ivory} o={0.4 + 0.6 * tw} />;
				})}
			</Svg>
		</AbsoluteFill>
	);
};

const sceneRelief: Scene = (ctx, a) => {
	const lt = ctx.t - ctx.cs(SCENE_AT.relief);
	const {petals, waves} = lotus(540, 820, 300);
	return (
		<AbsoluteFill style={{opacity: a}}>
			<Glow x={540} y={820} r={480} color="rgba(170,120,230,0.5)" o={easeOut(prog(lt, 0, 1.2))} />
			<Svg>
				<DrawAll ds={petals} p={easeInOut(prog(lt, 0.1, 2.4))} w={4} />
				<DrawAll ds={waves} p={easeOut(prog(lt, 1.2, 1.4))} seq={false} w={3} o={0.8} />
				<Draw d={circle(540, 780, 380, -90)} p={easeInOut(prog(lt, 0, 2.8))} w={2.5} c={C.ivory} o={0.7} />
				<Draw d={circle(540, 780, 400, 90)} p={easeInOut(prog(lt, 0.4, 2.8))} w={1.5} c={C.ivory} o={0.45} />
				<DrawAll ds={crescent(820, 420, 70)} p={easeOut(prog(lt, 0.8, 1.5))} w={3.5} />
				{[[250, 470, 26], [870, 1130, 22], [200, 1080, 18], [700, 340, 16]].map(([x, y, r], i) => {
					const tw = 0.5 + 0.5 * Math.sin(ctx.t * 2.5 + i * 2);
					return <Draw key={i} d={sparkle(x, y, r * (0.7 + 0.3 * tw))} p={prog(lt, 1 + i * 0.25, 0.5)} w={2.5} c={C.ivory} o={0.5 + 0.5 * tw} />;
				})}
			</Svg>
		</AbsoluteFill>
	);
};

const Palm: React.FC<{ctx: Ctx; lt: number; lineStart: number; lineDur: number; children?: React.ReactNode; labelAt: number; width?: number}> = ({ctx, lt, lineStart, lineDur, children, labelAt, width = 10}) => {
	const [x0, y0, x1, y1] = ctx.palmRect;
	const lp = easeInOut(prog(lt, lineStart, lineDur));
	const top = ctx.sun[ctx.sun.length - 1];
	const left = top[0] > PALM_C[0] + 60;
	const lx = top[0] + (left ? -190 : 190), ly = top[1] - 70;
	const pa = easeOut(prog(lt, labelAt, 0.5));
	const zoom = 1.04 - 0.04 * easeOut(prog(lt, 0, 1.2));
	return (
		<>
			<Glow x={PALM_C[0]} y={PALM_C[1]} r={600} color="rgba(138,92,200,0.45)" o={1} />
			<Img src={staticFile(PALM_FILE)} style={{position: 'absolute', left: x0, top: y0, width: x1 - x0, height: y1 - y0, borderRadius: 44,
				objectFit: 'cover', opacity: easeOut(prog(lt, 0, 0.6)), transform: `scale(${zoom})`, boxShadow: '0 20px 60px rgba(0,0,0,0.5)'}} />
			<Svg>
				<Draw d={rrect(x0 - 14, y0 - 14, x1 + 14, y1 + 14, 56)} p={easeInOut(prog(lt, 0.1, 1.4))} w={3} />
				<Draw d={rrect(x0 - 26, y0 - 26, x1 + 26, y1 + 26, 66)} p={easeInOut(prog(lt, 0.3, 1.6))} w={1.5} o={0.6} />
				{([[x0 - 20, y0 - 20], [x1 + 20, y0 - 20], [x0 - 20, y1 + 20], [x1 + 20, y1 + 20]] as Pt[]).map(([x, y], i) => (
					<Draw key={i} d={sparkle(x, y, 22)} p={prog(lt, 1.2, 0.5)} w={2.5} c={C.ivory} />
				))}
				<g filter="url(#glowBig)">
					<Draw d={poly(ctx.sun)} p={lp} w={width} c={C.sun} glow={false} />
				</g>
				<Draw d={poly([[top[0] + (left ? -14 : 14), top[1] - 8], [lx + (left ? 90 : -90), ly + 8]])} p={pa} w={3} c={C.sun} />
				{children}
			</Svg>
			{pa > 0 && (
				<div style={{position: 'absolute', left: lx, top: ly - 10 * (1 - pa), transform: 'translate(-50%,-50%)', opacity: pa, background: 'rgba(30,18,60,0.88)',
					border: `3px solid ${C.sun}`, borderRadius: 40, padding: '8px 28px', fontFamily: MARU, fontWeight: 700, fontSize: 46, color: '#FFE2A6',
					whiteSpace: 'nowrap'}}>太陽線</div>
			)}
		</>
	);
};

const scenePalm: Scene = (ctx, a) => {
	const t0 = ctx.cs(SCENE_AT.palm);
	const lt = ctx.t - t0;
	const line = ctx.sun;
	const top = line[line.length - 1];
	const tb = ctx.cs(7) - t0; // 良さが伝わった瞬間に → 光が放たれる
	const tc = ctx.cs(8) - t0; // 爆発的にお金が巡る → 光が手のまわりを巡る
	const u = ((lt - 2.05) * 0.6) % 1;
	const runner = line[Math.min(line.length - 1, Math.floor(clamp(u) * (line.length - 1)))];
	const k = easeOut(prog(lt, tc, 0.8));
	const [x0, y0, x1, y1] = ctx.palmRect;
	return (
		<AbsoluteFill style={{opacity: a}}>
			<Palm ctx={ctx} lt={lt} lineStart={0.25} lineDur={1.8} labelAt={1.9} width={lt > tc ? 10 + 4 * Math.sin((lt - tc) * 6) : 10}>
				{lt > 2.05 && <circle cx={runner[0]} cy={runner[1]} r={9} fill={C.ivory} opacity={Math.sin(u * Math.PI)} filter="url(#glow)" />}
				{lt > tb && sunRays(top[0], top[1], 26, 12, lt * 12).map((d, i) => <Draw key={i} d={d} p={easeOut(prog(lt, tb + i * 0.03, 0.6))} w={4} c={C.sun} />)}
				{lt > tc && Array.from({length: 10}, (_, i) => {
					const ang = (lt - tc) * 1.6 + (i * Math.PI * 2) / 10;
					const sx = PALM_C[0] + (x1 - x0) * 0.56 * Math.cos(ang) * k, sy = PALM_C[1] + (y1 - y0) * 0.5 * Math.sin(ang) * k;
					return <Draw key={i} d={sparkle(sx, sy, 16 + 6 * Math.sin(lt * 4 + i))} w={2.5} c={C.ivory} o={k} />;
				})}
				{lt > tc && <Draw d={circle(PALM_C[0], PALM_C[1], Math.max(1, 520 * k), (lt - tc) * 60)} w={2} o={k * (1 - prog(lt, tc + 0.8, 1.2))} />}
			</Palm>
			{lt > tb && <Glow x={top[0]} y={top[1]} r={260} color="rgba(255,194,102,0.7)" o={0.6 * easeOut(prog(lt, tb, 0.8))} />}
		</AbsoluteFill>
	);
};

const boxPaths = (cx: number, cy: number, s: number) => [rrect(cx - s, cy - s, cx + s, cy + s, 30), rrect(cx - s - 18, cy - s - 18, cx + s + 18, cy + s + 18, 40)];
const bars = (cx: number, cy: number, s: number, n = 6) =>
	Array.from({length: n}, (_, i) => {
		const x = cx - s + ((i + 1) * 2 * s) / (n + 1);
		return poly([[x, cy - s + 6], [x, cy + s - 6]]);
	});

const sceneBox: Scene = (ctx, a) => {
	const t0 = ctx.cs(SCENE_AT.box);
	const lt = ctx.t - t0;
	const tw = 0.5 + 0.5 * Math.sin(ctx.t * 1.6);
	const tb = ctx.cs(11) - t0; // 良さが出せない環境 → 格子が下りる
	return (
		<AbsoluteFill style={{opacity: a}}>
			<Svg>
				<DrawAll ds={boxPaths(540, 800, 250)} p={easeInOut(prog(lt, 0, 1.6))} w={3.5} o={0.85} />
				<path d={star5(540, 800, 46)} fill={C.ivory} opacity={(0.35 + 0.15 * tw) * prog(lt, 1, 0.8)} filter="url(#glow)" />
				<Draw d={star5(540, 800, 46)} p={easeOut(prog(lt, 0.9, 1))} w={2.5} c={C.ivory} o={0.7} />
				<DrawAll ds={bars(540, 800, 250)} p={easeInOut(prog(lt, tb, 1.2))} seq={false} w={3} c={C.ivory} o={0.55} />
				{[[230, 470], [860, 500], [850, 1110], [230, 1130]].map(([x, y], i) => (
					<Draw key={i} d={sparkle(x, y, 16)} p={prog(lt, 0.8 + i * 0.2, 0.5)} w={2} o={0.5} />
				))}
			</Svg>
		</AbsoluteFill>
	);
};

const sceneChange: Scene = (ctx, a) => {
	const t0 = ctx.cs(SCENE_AT.change);
	const lt = ctx.t - t0;
	const cx = 540, cy = 800;
	const tb = ctx.cs(13) - t0; // 場所が変わった瞬間
	const tc = ctx.cs(14) - t0; // 一気に評価とお金
	const open = easeInOut(prog(lt, tb, 0.9));
	const g = easeOut(prog(lt, tb + 0.2, 1.2));
	const sy = cy - 90 * g, sr = 46 + 70 * g;
	const k = lt - tc;
	const {petals} = lotus(cx, sy + 290, 170);
	return (
		<AbsoluteFill style={{opacity: a}}>
			<Glow x={cx} y={sy} r={200 + 300 * g} color="rgba(255,194,102,0.75)" o={0.15 + 0.7 * g} />
			<Svg>
				<DrawAll ds={boxPaths(cx, cy, 250)} p={1 - open} seq={false} w={3.5} o={0.85} />
				<DrawAll ds={bars(cx, cy, 250)} p={1} seq={false} w={3} c={C.ivory} o={0.55 * (1 - prog(lt, tb - 0.3, 0.5))} />
				<path d={star5(cx, sy, sr, lt * 10 * g)} fill={C.ivory} opacity={0.45 + 0.55 * g} filter="url(#glow)" />
				{g > 0 && Array.from({length: 16}, (_, i) => {
					const ang = ((i * 22.5 + lt * 8) * Math.PI) / 180;
					const r0 = sr + 30, r1 = sr + 30 + (i % 2 ? 110 : 70) * g;
					return <Draw key={i} d={poly([[cx + r0 * Math.cos(ang), sy + r0 * Math.sin(ang)], [cx + r1 * Math.cos(ang), sy + r1 * Math.sin(ang)]])}
						p={easeOut(prog(lt, tb + 0.4 + i * 0.03, 0.5))} w={3.5} />;
				})}
				{g > 0 && <DrawAll ds={petals} p={easeInOut(prog(lt, tb + 0.6, 1.6))} w={3} o={0.9} />}
				{k > 0 && [0, 1, 2].map((i) => {
					const ph = (k * 0.7 + i / 3) % 1;
					return <Draw key={i} d={circle(cx, sy, sr + 60 + 420 * ph)} w={2} o={(1 - ph) * prog(k, 0, 0.4)} />;
				})}
				{k > 0 && Array.from({length: 26}, (_, i) => {
					const x = 140 + random(`rx${i}`) * 800;
					const yy = 1250 - ((k * 0.22 + random(`ro${i}`)) % 1) * 1000;
					const tw = 0.5 + 0.5 * Math.sin(k * 5 + random(`rp${i}`) * 6.28);
					return <Draw key={i} d={sparkle(x, yy, (9 + random(`rs${i}`) * 13) * (0.6 + 0.4 * tw))} w={2.2} c={C.ivory} o={prog(k, 0, 0.5) * (0.4 + 0.6 * tw)} />;
				})}
			</Svg>
		</AbsoluteFill>
	);
};

const scenePalmAgain: Scene = (ctx, a) => {
	const t0 = ctx.cs(SCENE_AT.palmAgain);
	const lt = ctx.t - t0;
	const pulse = lt > 1.3 ? 0.5 + 0.5 * Math.sin((lt - 1.3) * 4) : 0;
	const tb = ctx.cs(16) - t0; // コメント欄に「太陽」
	const pa = easeBack(prog(lt, tb, 0.45));
	const n = Math.floor(clamp((lt - tb - 0.6) / 0.35, 0, 2));
	const top = ctx.sun[ctx.sun.length - 1];
	return (
		<AbsoluteFill style={{opacity: a}}>
			<Palm ctx={ctx} lt={lt} lineStart={0.3} lineDur={1} labelAt={1.2} width={10 + 5 * pulse} />
			<Glow x={top[0]} y={top[1]} r={200} color="rgba(255,194,102,0.7)" o={0.4 * pulse} />
			{pa > 0 && (
				<div style={{position: 'absolute', left: 90, top: 1165, width: 900, height: 120, borderRadius: 60, background: 'rgba(255,255,255,0.96)',
					opacity: clamp(pa), transform: `scale(${0.9 + 0.1 * pa})`, display: 'flex', alignItems: 'center', gap: 22, padding: '0 30px 0 18px',
					fontFamily: UD, fontSize: 44, boxShadow: '0 16px 40px rgba(0,0,0,0.4)'}}>
					<Avatar size={84} />
					<div style={{flex: 1, display: 'flex', alignItems: 'center', color: n ? '#222' : '#A0A4AC'}}>
						{n ? '太陽'.slice(0, n) : 'コメントを追加…'}
						{(Math.floor(lt * 2.5) % 2 === 0 || n < 2) && <span style={{width: 3, height: 56, background: '#3B82F6', marginLeft: 4}} />}
						{n === 2 && (
							<svg width={90} height={90} style={{marginLeft: 16}} viewBox="0 0 90 90">
								<DrawAll ds={[circle(45, 45, 16), ...sunRays(45, 45, 16, 10, (lt - tb) * 30)]} p={easeOut(prog(lt, tb + 1.3, 0.6))} w={3} c={C.sun} glow={false} />
							</svg>
						)}
					</div>
					<div style={{fontWeight: 700, fontSize: 38, color: n === 2 ? '#3B82F6' : '#A9C4F5'}}>投稿する</div>
				</div>
			)}
		</AbsoluteFill>
	);
};

const sceneEnd: Scene = (ctx, a) => {
	const lt = ctx.t - ctx.cs(SCENE_AT.end);
	const {rings, pet} = mandala(540, 640, 300, lt * 6);
	const pa = easeBack(prog(lt, 0.6, 0.5));
	const pulse = 1 + 0.035 * Math.sin(lt * 4) * prog(lt, 1.2, 0.5);
	return (
		<AbsoluteFill style={{opacity: a}}>
			<Glow x={540} y={640} r={520} color="rgba(170,120,230,0.5)" o={1} />
			<Glow x={540} y={640} r={200} color="rgba(255,194,102,0.7)" o={0.6 * prog(lt, 1, 1)} />
			<Svg>
				<DrawAll ds={rings} p={easeInOut(prog(lt, 0, 1.6))} seq={false} w={3} />
				<DrawAll ds={pet} p={easeInOut(prog(lt, 0.3, 2))} seq={false} w={2.5} />
				<DrawAll ds={[circle(540, 640, 44), ...sunRays(540, 640, 44, 12, -lt * 10)]} p={easeOut(prog(lt, 0.8, 1.2))} w={4} c={C.sun} />
				{[0, 1, 2].map((i) => {
					const y = 1225 + i * 30;
					const ph = (lt * 1.4 + i * 0.25) % 1;
					return <Draw key={i} d={poly([[500, y + 22], [540, y], [580, y + 22]])} p={prog(lt, 1.2, 0.4)} w={4} o={0.3 + 0.7 * Math.sin(ph * Math.PI)} />;
				})}
			</Svg>
			<div style={{position: 'absolute', top: 985, left: 0, right: 0, textAlign: 'center', fontFamily: MARU, fontWeight: 700, fontSize: 44, color: C.ivory,
				opacity: prog(lt, 0.9, 0.4), textShadow: '0 2px 10px rgba(0,0,0,0.6)'}}>プロフィールのリンクから</div>
			{pa > 0 && (
				<div style={{position: 'absolute', left: 140, top: 1055, width: 800, height: 150, borderRadius: 75, background: '#06C755', color: 'white',
					display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: MARU, fontWeight: 700, fontSize: 56, opacity: clamp(pa),
					transform: `scale(${pa * pulse})`, boxShadow: '0 0 40px rgba(6,199,85,0.55)'}}>公式LINEで無料鑑定</div>
			)}
		</AbsoluteFill>
	);
};

const SCENES: [number, Scene][] = [
	[SCENE_AT.chat, sceneChat], [SCENE_AT.relief, sceneRelief], [SCENE_AT.palm, scenePalm], [SCENE_AT.box, sceneBox],
	[SCENE_AT.change, sceneChange], [SCENE_AT.palmAgain, scenePalmAgain], [SCENE_AT.end, sceneEnd],
];

// ================================================================ main

export const TesouVideo: React.FC<VideoProps> = (props) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = frame / fps;
	const cues = props.cues.length ? props.cues : CUES.map((_, i) => ({start: i * 3, end: i * 3 + 3}));
	const [iw, ih] = props.palmSize;
	const s = Math.min(PALM_BOX[0] / iw, PALM_BOX[1] / ih);
	const pw = iw * s, ph = ih * s;
	const palmRect: Ctx['palmRect'] = [PALM_C[0] - pw / 2, PALM_C[1] - ph / 2, PALM_C[0] + pw / 2, PALM_C[1] + ph / 2];
	const pts = [...props.sunline].sort((p, q) => q[1] - p[1]).map(([u, v]) => [palmRect[0] + pw * u, palmRect[1] + ph * v] as Pt);
	const ctx: Ctx = {...props, cues, t, cs: (i) => (i === 0 ? 0 : cues[i].start), palmRect, sun: smooth(pts)};

	const starts = SCENES.map(([i]) => ctx.cs(i));
	let idx = 0;
	starts.forEach((st, i) => {
		if (t >= st) idx = i;
	});
	const p = prog(t, starts[idx], XFADE);
	const cue = cues.findIndex((c) => c.start <= t && t < c.end);

	return (
		<AbsoluteFill>
			<GlowDefs />
			<Audio src={staticFile(AUDIO_FILE)} />
			<Background t={t} />
			{idx > 0 && p < 1 && SCENES[idx - 1][1](ctx, 1 - p)}
			{SCENES[idx][1](ctx, idx > 0 ? p : 1)}
			<Title t={t} />
			{cue >= 0 && <Telop text={CUES[cue].text} k={easeOut(prog(t, cues[cue].start, 0.22))} />}
		</AbsoluteFill>
	);
};
