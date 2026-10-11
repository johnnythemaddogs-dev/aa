// 台本。text の \n が改行位置 (それ以外では改行しない)、[ ] で囲んだ語は金色で強調。
// narration は読み上げ原稿で、テロップの時間配分の目安に使う。
export const CUES: {text: string; narration: string}[] = [
	{text: '[無料鑑定]で\nこんな相談をいただきました', narration: '無料鑑定で、こんな相談をいただきました。'},
	{text: '「両手に[太陽線]があるのに\n全然お金も人気もありません…」', narration: '「両手に太陽線があるのに、全然お金もにんきもありません…」'},
	{text: '実は 同じように悩んでいる人\nすごく多いんです', narration: '実は、同じように悩んでいる人、すごく多いんです。'},
	{text: 'でも 安心してください', narration: 'でも安心してください。'},
	{text: 'あなたの手相が間違っている\nわけではありません', narration: 'あなたの手相が間違っているわけではありません。'},
	{text: '[太陽線]は', narration: '太陽線は、'},
	{text: '「勝手に大金持ちになる線」\nではなく', narration: '「勝手に大金持ちになる線」ではなく、'},
	{text: '「あなたの[良さ]が\n人に伝わった瞬間に', narration: '「あなたの良さが人に伝わった瞬間に、'},
	{text: '[爆発的にお金が巡る線]」\nなんです', narration: '爆発的にお金が巡る線」なんです。'},
	{text: '今 お金がないと\n感じているなら', narration: '今お金がないと感じているなら、'},
	{text: 'それは 才能がないのではなく', narration: 'それは才能がないのではなく、'},
	{text: '「自分の良さが出せない環境」\nにいるだけ', narration: '「自分の良さが出せない環境」にいるだけ。'},
	{text: 'ただ決められた作業を\nこなす場所から', narration: 'ただ決められた作業をこなす場所から、'},
	{text: 'あなたの人柄やセンスが\n人に伝わる場所に変わった瞬間', narration: 'あなたの人柄やセンスが人に伝わる場所に変わった瞬間、'},
	{text: '一気に[評価]と[お金]が\nついてきますよ', narration: '一気に評価とお金がついてきますよ。'},
	{text: 'あなたの手には\n[太陽線]がありましたか？', narration: 'あなたの手には、太陽線がありましたか？'},
	{text: 'あった人はコメント欄に\n「[太陽]」と書いてね', narration: 'あった人はコメント欄に「太陽」と書いてね。'},
	{text: 'あなた自身の手相を\nもっと詳しく知りたい方は', narration: 'あなた自身の手相をもっと詳しく知りたい方は、'},
	{text: 'プロフィールのリンクから\n[公式LINE]で[無料鑑定]しています', narration: 'プロフィールのリンクから、公式LINEで無料鑑定しています。'},
];

export const TITLE = '太陽線があるのに お金がない理由';

// 場面の切り替わり (何番目のテロップから始まるか。0 始まり)
export const SCENE_AT = {
	chat: 0,
	relief: 3,
	palm: 5,
	box: 9,
	change: 12,
	palmAgain: 15,
	end: 17,
} as const;

// 太陽線: 手のひら画像内の位置を割合 (左上 0,0 / 右下 1,1) で。手首側 → 指側の順
export const DEFAULT_SUNLINE: [number, number][] = [
	[0.62, 0.68],
	[0.615, 0.56],
	[0.605, 0.43],
];

export const AUDIO_FILE = 'narration.wav';
export const PALM_FILE = 'palm.png';
export const TIMINGS_FILE = 'timings.json'; // 任意: [[開始秒, 終了秒], ...] で手動指定
export const TAIL_SEC = 1.5;
