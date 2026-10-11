#!/usr/bin/env bash
# 猫の愛情表現をテーマにした「動画編集デモ」を一括生成する。
# 前提: render_cats.py / make_audio.py / make_stickers.py で ../src に素材があること。
# 使い方: scripts/edit_demos.sh [デモ番号...]   （省略時は全部）
set -euo pipefail
cd "$(dirname "$0")/.."
S=src
O=out
T=out/.tmp
mkdir -p "$O" "$T"
F=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc
FF="ffmpeg -y -hide_banner -loglevel error"
ENC="-c:v libx264 -pix_fmt yuv420p -crf 21 -preset medium -c:a aac -b:a 128k -movflags +faststart"
TXT="fontfile=$F:fontcolor=white:borderw=4:bordercolor=0x000000@0.6"

# 右上にデモ名の小さなタグを付けて out/ に書き出す
finish() { # finish <tmp> <name> <タグ文字列>
  $FF -i "$1" -vf "drawtext=$TXT:fontsize=16:text='$3':x=w-tw-12:y=10:box=1:boxcolor=0xE85A82@0.85:boxborderw=6:borderw=0" \
    $ENC "$O/$2.mp4"
  echo "  -> $O/$2.mp4"
}

demo_01() { # カット編集（ジャンプカット）
  $FF -i $S/blink.mp4 -i $S/headbump.mp4 -i $S/knead.mp4 -filter_complex "
    [0:v]trim=1.0:2.8,setpts=PTS-STARTPTS[v0];[0:a]atrim=1.0:2.8,asetpts=PTS-STARTPTS[a0];
    [1:v]trim=2.0:3.6,setpts=PTS-STARTPTS[v1];[1:a]atrim=2.0:3.6,asetpts=PTS-STARTPTS[a1];
    [2:v]trim=0.5:2.1,setpts=PTS-STARTPTS[v2];[2:a]atrim=0.5:2.1,asetpts=PTS-STARTPTS[a2];
    [v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]" -map "[v]" -map "[a]" $ENC $T/01.mp4
  finish $T/01.mp4 01_cut "01 カット編集"
}

demo_02() { # トランジション（4 種）
  $FF -i $S/blink.mp4 -i $S/headbump.mp4 -i $S/knead.mp4 -i $S/tail.mp4 -i $S/bgm.wav -filter_complex "
    [0:v]trim=1.8:3.6,setpts=PTS-STARTPTS[a];[1:v]trim=2.0:3.8,setpts=PTS-STARTPTS[b];
    [2:v]trim=0:1.8,setpts=PTS-STARTPTS[c];[3:v]trim=3.0:4.8,setpts=PTS-STARTPTS[d];
    [a][b]xfade=transition=circleopen:duration=0.5:offset=1.3[ab];
    [ab][c]xfade=transition=slideleft:duration=0.5:offset=2.6[abc];
    [abc][d]xfade=transition=heartgrow:duration=0.5:offset=3.9[v];
    [4:a]atrim=0:5.4,afade=t=out:st=4.6:d=0.8[aa]" -map "[v]" -map "[aa]" $ENC $T/02.mp4 2>/dev/null || \
  $FF -i $S/blink.mp4 -i $S/headbump.mp4 -i $S/knead.mp4 -i $S/tail.mp4 -i $S/bgm.wav -filter_complex "
    [0:v]trim=1.8:3.6,setpts=PTS-STARTPTS[a];[1:v]trim=2.0:3.8,setpts=PTS-STARTPTS[b];
    [2:v]trim=0:1.8,setpts=PTS-STARTPTS[c];[3:v]trim=3.0:4.8,setpts=PTS-STARTPTS[d];
    [a][b]xfade=transition=circleopen:duration=0.5:offset=1.3[ab];
    [ab][c]xfade=transition=slideleft:duration=0.5:offset=2.6[abc];
    [abc][d]xfade=transition=radial:duration=0.5:offset=3.9[v];
    [4:a]atrim=0:5.4,afade=t=out:st=4.6:d=0.8[aa]" -map "[v]" -map "[aa]" $ENC $T/02.mp4
  finish $T/02.mp4 02_transition "02 トランジション"
}

demo_03() { # スローモーション
  $FF -i $S/blink.mp4 -filter_complex "
    [0:v]trim=1.0:3.5,setpts=2*(PTS-STARTPTS)[v];[0:a]atrim=1.0:3.5,asetpts=PTS-STARTPTS,atempo=0.5[a]" \
    -map "[v]" -map "[a]" $ENC $T/03.mp4
  finish $T/03.mp4 03_slowmo "03 スローモーション(0.5倍)"
}

demo_04() { # フレーム補間スロー（比較）
  $FF -i $S/headbump.mp4 -filter_complex "
    [0:v]trim=0.6:2.6,setpts=PTS-STARTPTS,fps=8,setpts=2.5*PTS,fps=24,scale=320:180,
      drawtext=$TXT:fontsize=18:text='単純スロー（カクカク）':x=(w-tw)/2:y=h-30[l];
    [0:v]trim=0.6:2.6,setpts=PTS-STARTPTS,fps=8,minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:vsbmc=1,setpts=2.5*PTS,fps=24,scale=320:180,
      drawtext=$TXT:fontsize=18:text='フレーム補間（なめらか）':x=(w-tw)/2:y=h-30[r];
    [l][r]hstack,pad=640:360:0:90:color=0x2b2233[v]" -map "[v]" -t 5 -an $ENC $T/04.mp4
  finish $T/04.mp4 04_interpolate "04 フレーム補間"
}

demo_05() { # 早送り（6 素材 36 秒 → 5 秒）
  $FF -i $S/blink.mp4 -i $S/headbump.mp4 -i $S/knead.mp4 -i $S/tail.mp4 -i $S/closeup.mp4 -i $S/bgm.wav -filter_complex "
    [0:v][1:v][2:v][3:v][4:v]concat=n=5:v=1:a=0,setpts=PTS/6,fps=24,
      drawtext=$TXT:fontsize=40:text='▶▶ ×6':x=20:y=h-60[v];[5:a]atrim=0:5,atempo=1.0,afade=t=out:st=4.3:d=0.7[a]" \
    -map "[v]" -map "[a]" -t 5 $ENC $T/05.mp4
  finish $T/05.mp4 05_fastforward "05 早送り"
}

demo_06() { # 逆再生
  $FF -i $S/tail.mp4 -filter_complex "[0:v]trim=0:5,setpts=PTS-STARTPTS,reverse,
      drawtext=$TXT:fontsize=36:text='◀◀ REWIND':x=20:y=h-56[v];[0:a]atrim=0:5,areverse[a]" \
    -map "[v]" -map "[a]" $ENC $T/06.mp4
  finish $T/06.mp4 06_reverse "06 逆再生"
}

demo_07() { # ブーメラン
  $FF -i $S/knead.mp4 -filter_complex "
    [0:v]trim=1.0:2.25,setpts=PTS-STARTPTS,split[f][r0];[r0]reverse[r];[f][r]concat=n=2,split[x][y];[x][y]concat=n=2[v]" \
    -map "[v]" -an $ENC $T/07.mp4
  finish $T/07.mp4 07_boomerang "07 ブーメラン"
}

demo_08() { # ズームイン／パン（ケン・バーンズ）
  $FF -i $S/closeup.mp4 -filter_complex "
    [0:v]trim=0:5,setpts=PTS-STARTPTS,scale=1920:1080,
    zoompan=z='1+0.9*on/120':d=1:x='iw/2-iw/zoom/2':y='ih*0.18-ih/zoom*0.18+on*0.6':s=640x360:fps=24[v]" \
    -map "[v]" -map 0:a -t 5 $ENC $T/08.mp4
  finish $T/08.mp4 08_zoom_pan "08 ズーム＆パン"
}

demo_09() { # 縦型（9:16）リフレーム＋背景ぼかし
  $FF -i $S/headbump.mp4 -filter_complex "
    [0:v]trim=0.5:5.5,setpts=PTS-STARTPTS,split[a][b];
    [a]scale=-2:640,crop=360:640,boxblur=18:2,eq=brightness=-0.05[bg];
    [b]crop=420:360:110:0,scale=360:-2[fg];
    [bg][fg]overlay=0:(H-h)/2,
      drawtext=$TXT:fontsize=30:text='すりすり♡':x=(w-tw)/2:y=90,
      drawtext=$TXT:fontsize=18:text='#猫の愛情表現 #ショート動画':x=(w-tw)/2:y=h-90[v];
    [0:a]atrim=0.5:5.5,asetpts=PTS-STARTPTS[aa]" -map "[v]" -map "[aa]" $ENC $T/09.mp4
  $FF -i $T/09.mp4 -vf "drawtext=$TXT:fontsize=14:text='09 縦型(9：16)変換':x=w-tw-10:y=10:box=1:boxcolor=0xE85A82@0.85:boxborderw=5:borderw=0" \
    $ENC $O/09_vertical.mp4; echo "  -> $O/09_vertical.mp4"
}

demo_10() { # 回転・反転
  $FF -i $S/knead.mp4 -filter_complex "
    [0:v]trim=0:5,setpts=PTS-STARTPTS,scale=320:180,split=4[a][b][c][d];
    [a]drawtext=$TXT:fontsize=18:text='元の映像':x=8:y=h-26[A];
    [b]hflip,drawtext=$TXT:fontsize=18:text='左右反転':x=8:y=h-26[B];
    [c]vflip,drawtext=$TXT:fontsize=18:text='上下反転':x=8:y=h-26[C];
    [d]rotate=a='2*PI*t/5':fillcolor=0x2b2233:ow=320:oh=180,drawtext=$TXT:fontsize=18:text='回転':x=8:y=h-26[D];
    [A][B][C][D]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[v]" -map "[v]" -map 0:a -t 5 $ENC $T/10.mp4
  finish $T/10.mp4 10_rotate_flip "10 回転・反転"
}

demo_11() { # カラーグレーディング（ビフォー／アフター ワイプ）
  $FF -i $S/blink.mp4 -filter_complex "
    [0:v]trim=0:5,setpts=PTS-STARTPTS,split[o][g0];
    [g0]curves=preset=lighter,colorbalance=rs=0.12:gs=0.02:bs=-0.12:rh=0.08:bh=-0.06,eq=saturation=1.35:contrast=1.08,vignette=PI/4[g];
    [o]drawtext=$TXT:fontsize=22:text='BEFORE':x=16:y=h-40[o2];
    [g]drawtext=$TXT:fontsize=22:text='AFTER（暖色グレード）':x=w-tw-16:y=h-40[g2];
    [g2][o2]blend=all_expr='if(lt(X, W*(0.5+0.35*sin(T*1.3))), B, A)'[m];
    [m]drawbox=x='trunc(iw*(0.5+0.35*sin(t*1.3)))':y=0:w=3:h=ih:color=white@0.9:t=fill[v]" \
    -map "[v]" -map 0:a -t 5 $ENC $T/11.mp4 2>/dev/null || \
  $FF -i $S/blink.mp4 -filter_complex "
    [0:v]trim=0:5,setpts=PTS-STARTPTS,split[o][g0];
    [g0]curves=preset=lighter,colorbalance=rs=0.12:gs=0.02:bs=-0.12:rh=0.08:bh=-0.06,eq=saturation=1.35:contrast=1.08,vignette=PI/4[g];
    [o]crop=320:360:0:0,drawtext=$TXT:fontsize=22:text='BEFORE':x=16:y=h-40[l];
    [g]crop=320:360:320:0,drawtext=$TXT:fontsize=22:text='AFTER':x=w-tw-16:y=h-40[r];
    [l][r]hstack,drawbox=x=319:y=0:w=3:h=ih:color=white:t=fill[v]" -map "[v]" -map 0:a -t 5 $ENC $T/11.mp4
  finish $T/11.mp4 11_color_grade "11 カラーグレーディング"
}

demo_12() { # フィルム風（セピア＋ノイズ＋ちらつき＋ビネット）
  $FF -i $S/headbump.mp4 -filter_complex "
    [0:v]trim=0.5:5.5,setpts=PTS-STARTPTS,colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,
      noise=alls=22:allf=t+u,eq=brightness='0.03*sin(t*37)':eval=frame,vignette=PI/3.5,
      pad=iw:ih:0:0,drawbox=x=0:y=0:w=iw:h=24:color=black:t=fill,drawbox=x=0:y=ih-24:w=iw:h=24:color=black:t=fill,
      drawbox=x='mod(trunc(t*24)*53,iw)':y=0:w=1:h=ih:color=white@0.25:t=fill[v];
    [0:a]atrim=0.5:5.5,asetpts=PTS-STARTPTS,highpass=f=300,lowpass=f=3000[a]" -map "[v]" -map "[a]" $ENC $T/12.mp4
  finish $T/12.mp4 12_film_retro "12 レトロフィルム風"
}

demo_13() { # アニメーションテロップ
  $FF -i $S/blink.mp4 -filter_complex "
    [0:v]trim=0.6:5.6,setpts=PTS-STARTPTS,
    drawbox=x=0:y='ih-90*min(1,t/0.4)':w=iw:h=90:color=0xE85A82@0.85:t=fill,
    drawtext=$TXT:fontsize=30:text='ゆっくりまばたき ＝ 猫のキス':x='max(30, w-(t-0.3)*1600)':y=h-72:alpha='min(1,max(0,(t-0.3)*3))',
    drawtext=$TXT:fontsize=20:fontcolor=0xFFF0F4:text='「あなたを信頼しているよ」のサイン':x=30:y=h-34:alpha='min(1,max(0,(t-1.0)*2))',
    drawtext=$TXT:fontsize='60+20*abs(sin(t*4))':fontcolor=0xFF6F9A:text='♡':x=w-110:y=40:enable='gt(t,2.0)'[v]" \
    -map "[v]" -map 0:a -t 5 $ENC $T/13.mp4
  finish $T/13.mp4 13_telop "13 テロップ"
}

demo_14() { # 字幕（ASS 字幕の焼き込み）
  cat > $T/knead.ass <<'EOF'
[Script Info]
ScriptType: v4.00+
PlayResX: 640
PlayResY: 360

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,WenQuanYi Zen Hei,26,&H00FFFFFF,&H00FFFFFF,&H00303030,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,20,20,22,1
Style: Kara,WenQuanYi Zen Hei,30,&H00FFFFFF,&H009A6FFF,&H00303030,&H80000000,1,0,0,0,100,100,0,0,1,3,1,8,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.20,0:00:01.80,Default,,0,0,0,,{\fad(200,200)}ふみふみ…ふみふみ…
Dialogue: 0,0:00:01.90,0:00:03.40,Default,,0,0,0,,{\fad(200,200)}子猫の頃、お母さんに甘えたしぐさ
Dialogue: 0,0:00:03.50,0:00:04.95,Default,,0,0,0,,{\fad(200,200)}{\c&H9A6FFF&}安心しきっている{\c&HFFFFFF&}証拠です
Dialogue: 0,0:00:00.20,0:00:04.95,Kara,,0,0,0,,{\k60}ゴ{\k60}ロ{\k60}ゴ{\k60}ロ{\k60}～{\k100}♪
EOF
  $FF -i $S/knead.mp4 -vf "subtitles=$T/knead.ass:fontsdir=/usr/share/fonts/truetype/wqy" -t 5 $ENC $T/14.mp4
  finish $T/14.mp4 14_subtitles "14 字幕(ASS/カラオケ)"
}

demo_15() { # ピクチャー・イン・ピクチャー
  $FF -i $S/headbump.mp4 -i $S/closeup.mp4 -filter_complex "
    [1:v]trim=0:5,setpts=PTS-STARTPTS,scale=200:-2,pad=iw+8:ih+8:4:4:color=white[p];
    [0:v]trim=0:5,setpts=PTS-STARTPTS[m];
    [m][p]overlay=x='W-w-16':y='H-h-16-max(0,(1-t*2))*200'[v]" -map "[v]" -map 0:a -t 5 $ENC $T/15.mp4
  finish $T/15.mp4 15_pip "15 ピクチャー・イン・ピクチャー"
}

demo_16() { # 分割画面（2×2）
  $FF -i $S/blink.mp4 -i $S/headbump.mp4 -i $S/knead.mp4 -i $S/tail.mp4 -filter_complex "
    [0:v]trim=1:6,setpts=PTS-STARTPTS,scale=320:180,drawtext=$TXT:fontsize=18:text='まばたき':x=8:y=h-26[a];
    [1:v]trim=1:6,setpts=PTS-STARTPTS,scale=320:180,drawtext=$TXT:fontsize=18:text='すりすり':x=8:y=h-26[b];
    [2:v]trim=0:5,setpts=PTS-STARTPTS,scale=320:180,drawtext=$TXT:fontsize=18:text='ふみふみ':x=8:y=h-26[c];
    [3:v]trim=1:6,setpts=PTS-STARTPTS,scale=320:180,drawtext=$TXT:fontsize=18:text='しっぽピーン':x=8:y=h-26[d];
    [a][b][c][d]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0,drawbox=x=318:y=0:w=4:h=ih:color=white:t=fill,drawbox=x=0:y=178:w=iw:h=4:color=white:t=fill[v]" \
    -map "[v]" -map 2:a -t 5 $ENC $T/16.mp4
  finish $T/16.mp4 16_split_screen "16 分割画面"
}

demo_17() { # クロマキー合成（グリーンバック）
  $FF -i $S/green.mp4 -f lavfi -i "gradients=s=640x360:c0=0xFFB6D9:c1=0x9AD0FF:c2=0xFFF2A8:n=3:speed=0.02:r=24" -i $S/bgm.wav -filter_complex "
    [0:v]trim=0:5,setpts=PTS-STARTPTS,chromakey=0x00C83C:0.12:0.05,despill=type=green[k];
    [1:v]trim=0:5,setpts=PTS-STARTPTS,drawtext=$TXT:fontsize=120:fontcolor=white@0.35:borderw=0:text='♡':x='60+20*sin(t*2)':y=60,
      drawtext=$TXT:fontsize=90:fontcolor=white@0.35:borderw=0:text='♡':x=w-160:y='200+20*sin(t*3)'[bg];
    [bg][k]overlay=0:0[v];[2:a]atrim=0:5,afade=t=out:st=4.3:d=0.7[a]" -map "[v]" -map "[a]" -t 5 $ENC $T/17.mp4
  finish $T/17.mp4 17_chromakey "17 クロマキー合成"
}

demo_18() { # モザイク → ぼかし
  $FF -i $S/closeup.mp4 -filter_complex "
    [0:v]trim=0:5,setpts=PTS-STARTPTS,split=3[base][m0][b0];
    [m0]crop=300:200:170:60,scale=15:10,scale=300:200:flags=neighbor[m];
    [b0]crop=300:200:170:60,boxblur=20:3[b];
    [base][m]overlay=170:60:enable='lt(t,2.5)'[x];[x][b]overlay=170:60:enable='gte(t,2.5)',
    drawtext=$TXT:fontsize=26:text='モザイク':x=20:y=h-50:enable='lt(t,2.5)',
    drawtext=$TXT:fontsize=26:text='ぼかし':x=20:y=h-50:enable='gte(t,2.5)'[v]" -map "[v]" -map 0:a -t 5 $ENC $T/18.mp4
  finish $T/18.mp4 18_mosaic_blur "18 モザイク・ぼかし"
}

demo_19() { # 手ブレ補正（vid.stab 2 パス）
  $FF -i $S/blink.mp4 -vf "scale=736:414,crop=640:360:'48+40*sin(t*7)+18*sin(t*17)':'27+22*sin(t*9+1)+10*sin(t*23)',rotate='0.025*sin(t*5)'" \
    -t 5 -an $ENC $T/shaky.mp4
  $FF -i $T/shaky.mp4 -vf vidstabdetect=shakiness=10:accuracy=15:result=$T/tr.trf -f null -
  $FF -i $T/shaky.mp4 -vf vidstabtransform=input=$T/tr.trf:smoothing=30:zoom=8,unsharp=5:5:0.6 -an $ENC $T/stab.mp4
  $FF -i $T/shaky.mp4 -i $T/stab.mp4 -i $S/blink.mp4 -filter_complex "
    [0:v]scale=320:180,drawtext=$TXT:fontsize=18:text='補正前（手ブレ）':x=(w-tw)/2:y=h-28[l];
    [1:v]scale=320:180,drawtext=$TXT:fontsize=18:text='補正後':x=(w-tw)/2:y=h-28[r];
    [l][r]hstack,pad=640:360:0:90:color=0x2b2233[v]" -map "[v]" -map 2:a -t 5 $ENC $T/19.mp4
  finish $T/19.mp4 19_stabilize "19 手ブレ補正"
}

demo_20() { # BGM・効果音・音量調整・ダッキング
  $FF -i $S/blink.mp4 -i $S/bgm.wav -i $S/chime.wav -filter_complex "
    [1:a]atrim=0:5,volume=0.55,afade=t=in:d=0.5,afade=t=out:st=4.2:d=0.8[bgm];
    [2:a]adelay=2200|2200,volume=0.9[sfx];
    [0:a]atrim=0:5,volume=2.2[purr];
    [bgm][purr]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[duck];
    [0:a]atrim=0:5,volume=2.2[purr2];
    [duck][purr2][sfx]amix=inputs=3:normalize=0,alimiter[a];
    [a]asplit[a1][a2];[a2]showwaves=s=640x70:mode=cline:colors=0xFF8FB1:scale=sqrt,format=rgba[w];
    [0:v]trim=0:5,setpts=PTS-STARTPTS[bv];[bv][w]overlay=0:H-74,
    drawtext=$TXT:fontsize=16:text='BGM＋ゴロゴロ音＋効果音(2.2秒)をミックス':x=12:y=h-96[v]" \
    -map "[v]" -map "[a1]" -t 5 $ENC $T/20.mp4
  finish $T/20.mp4 20_audio_mix "20 BGM・効果音ミックス"
}

demo_21() { # フェードイン・アウト（黒／白）
  $FF -i $S/tail.mp4 -i $S/bgm.wav -filter_complex "
    [0:v]trim=0.5:5.5,setpts=PTS-STARTPTS,fade=t=in:st=0:d=1.2,fade=t=out:st=3.8:d=1.2:color=white[v];
    [1:a]atrim=0:5,afade=t=in:d=1.2,afade=t=out:st=3.8:d=1.2[a]" -map "[v]" -map "[a]" $ENC $T/21.mp4
  finish $T/21.mp4 21_fade "21 フェードイン・アウト"
}

demo_22() { # スライドショー（静止画から）
  for i in "blink 3.3" "headbump 3.2" "knead 2.0" "tail 4.6" "closeup 1.0"; do
    set -- $i; $FF -ss $2 -i $S/$1.mp4 -frames:v 1 $T/still_$1.png
  done
  $FF -loop 1 -t 1.6 -i $T/still_blink.png -loop 1 -t 1.6 -i $T/still_headbump.png -loop 1 -t 1.6 -i $T/still_knead.png \
      -loop 1 -t 1.6 -i $T/still_tail.png -i $S/bgm.wav -filter_complex "
    [0:v]scale=1280:720,zoompan=z='1+0.0035*on':d=1:s=640x360:fps=24,pad=640:360,drawbox=x=0:y=0:w=iw:h=ih:color=white:t=14[a];
    [1:v]scale=1280:720,zoompan=z='1.2-0.0035*on':d=1:x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':s=640x360:fps=24,drawbox=x=0:y=0:w=iw:h=ih:color=white:t=14[b];
    [2:v]scale=1280:720,zoompan=z='1.1':d=1:x='on*3':y='ih/2-ih/zoom/2':s=640x360:fps=24,drawbox=x=0:y=0:w=iw:h=ih:color=white:t=14[c];
    [3:v]scale=1280:720,zoompan=z='1+0.0035*on':d=1:x='iw/2-iw/zoom/2':y='ih/4-ih/zoom/4':s=640x360:fps=24,drawbox=x=0:y=0:w=iw:h=ih:color=white:t=14[d];
    [a][b]xfade=transition=fade:duration=0.4:offset=1.2[ab];[ab][c]xfade=transition=fade:duration=0.4:offset=2.4[abc];
    [abc][d]xfade=transition=fade:duration=0.4:offset=3.6,format=yuv420p[v];
    [4:a]atrim=0:5.2,afade=t=out:st=4.4:d=0.8[aa]" -map "[v]" -map "[aa]" $ENC $T/22.mp4
  finish $T/22.mp4 22_slideshow "22 写真スライドショー"
}

demo_23() { # フリーズフレーム＋強調
  # 2.4 秒（58 フレーム目）で 1.5 秒静止し、フラッシュ＋ズーム＋文字
  $FF -i $S/blink.mp4 -filter_complex "
    [0:v]trim=1.0:4.5,setpts=PTS-STARTPTS,loop=loop=36:size=1:start=34,setpts=N/24/TB,
      zoompan=z='if(between(on,34,70),1+0.4*min(1,(on-34)/8),1)':d=1:x='iw/2-iw/zoom/2':y='ih*0.25-ih/zoom*0.25':s=640x360:fps=24,
      eq=brightness='if(between(n,34,37),0.5-0.15*(n-34),0)':eval=frame,
      drawtext=$TXT:fontsize=40:fontcolor=0xFFE15A:text='いまの、猫キス！':x=(w-tw)/2:y=h-80:enable='between(n,36,70)'[v];
    [0:a]atrim=1.0:6,asetpts=PTS-STARTPTS[a]" -map "[v]" -map "[a]" -t 5 $ENC $T/23.mp4
  finish $T/23.mp4 23_freeze_frame "23 フリーズフレーム"
}

demo_24() { # スピードランプ（速→超スロー→速）
  $FF -i $S/headbump.mp4 -filter_complex "
    [0:v]split=3[x][y][z];
    [x]trim=0:2.0,setpts=(PTS-STARTPTS)/2[a];
    [y]trim=2.0:3.4,setpts=(PTS-STARTPTS)*2.5,minterpolate=fps=24:mi_mode=blend[b];
    [z]trim=3.4:4.4,setpts=(PTS-STARTPTS)/2[c];
    [a][b][c]concat=n=3,fps=24,
      drawtext=$TXT:fontsize=30:text='×2':x=20:y=h-56:enable='lt(t,1)+gte(t,4.5)',
      drawtext=$TXT:fontsize=30:text='×0.4 スロー':x=20:y=h-56:enable='between(t,1,4.5)'[v]" \
    -map "[v]" -an -t 5 $ENC $T/24.mp4
  finish $T/24.mp4 24_speed_ramp "24 スピードランプ"
}

demo_25() { # ミラー・万華鏡
  $FF -i $S/headbump.mp4 -filter_complex "
    [0:v]trim=1:6,setpts=PTS-STARTPTS,crop=320:360:0:0,split[l][r0];[r0]hflip[r];[l][r]hstack,split[m][n];
    [m]scale=320:180,split[q1][q2];[q2]vflip[q3];[q1][q3]vstack,split[c1][c2];[c2]hflip[c3];[c1][c3]hstack[k];
    [n]crop=640:360[mm];
    [mm][k]xfade=transition=fadeblack:duration=0.6:offset=2.2[v]" -map "[v]" -map 0:a -t 5 $ENC $T/25.mp4
  finish $T/25.mp4 25_mirror "25 ミラー・万華鏡"
}

demo_26() { # グリッチ
  $FF -i $S/tail.mp4 -filter_complex "
    [0:v]trim=0.5:5.5,setpts=PTS-STARTPTS,
      rgbashift=rh='if(lt(mod(t,1.1),0.18),14,0)':bh='if(lt(mod(t,1.1),0.18),-14,0)':gv='if(lt(mod(t,0.7),0.08),6,0)',
      noise=alls='if(lt(mod(t,1.1),0.18),40,4)':allf=t,
      hue=H='if(lt(mod(t,1.3),0.06),PI/2,0)',
      drawbox=x=0:y='mod(trunc(t*24)*37,ih)':w=iw:h=6:color=white@0.35:t=fill:enable='lt(mod(t,1.1),0.18)'[v];
    [0:a]atrim=0.5:5.5,asetpts=PTS-STARTPTS[a]" -map "[v]" -map "[a]" $ENC $T/26.mp4 2>/dev/null || \
  $FF -i $S/tail.mp4 -filter_complex "
    [0:v]trim=0.5:5.5,setpts=PTS-STARTPTS,split[a][b];[b]rgbashift=rh=14:bh=-14:gv=6,noise=alls=40:allf=t[g];
    [a][g]overlay=enable='lt(mod(t,1.1),0.18)',
      drawbox=x=0:y='mod(trunc(t*24)*37,ih)':w=iw:h=6:color=white@0.35:t=fill:enable='lt(mod(t,1.1),0.18)'[v];
    [0:a]atrim=0.5:5.5,asetpts=PTS-STARTPTS[aa]" -map "[v]" -map "[aa]" $ENC $T/26.mp4
  finish $T/26.mp4 26_glitch "26 グリッチ"
}

demo_27() { # コマ撮り（ストップモーション）風
  $FF -i $S/knead.mp4 -filter_complex "
    [0:v]trim=0:5,setpts=PTS-STARTPTS,fps=6,scale=672:378,crop=640:360:'16+8*sin(n*12.9)':'9+6*cos(n*7.3)',
      eq=brightness='0.02*sin(n*5.1)':eval=frame,fps=24[v]" -map "[v]" -map 0:a -t 5 $ENC $T/27.mp4
  finish $T/27.mp4 27_stop_motion "27 コマ撮り風"
}

demo_28() { # アート系フィルター
  $FF -i $S/closeup.mp4 -filter_complex "
    [0:v]trim=0:5,setpts=PTS-STARTPTS,scale=320:180,split=4[a][b][c][d];
    [a]edgedetect=mode=colormix:high=0.15,drawtext=$TXT:fontsize=18:text='線画風':x=8:y=h-26[A];
    [b]lutrgb=r='trunc(val/64)*64+32':g='trunc(val/64)*64+32':b='trunc(val/64)*64+32',drawtext=$TXT:fontsize=18:text='ポスタライズ':x=8:y=h-26[B];
    [c]negate,drawtext=$TXT:fontsize=18:text='ネガ反転':x=8:y=h-26[C];
    [d]hue=h='t*144',drawtext=$TXT:fontsize=18:text='色相回転':x=8:y=h-26[D];
    [A][B][C][D]xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[v]" -map "[v]" -map 0:a -t 5 $ENC $T/28.mp4
  finish $T/28.mp4 28_art_filters "28 アート系フィルター"
}

demo_29() { # ステッカー・アニメーション合成＋効果音
  $FF -i $S/knead.mp4 -loop 1 -i $S/heart.png -loop 1 -i $S/bubble.png -i $S/pop.wav -filter_complex "
    [1:v]format=rgba,scale=w='120*(0.8+0.25*abs(sin(t*6)))':h=-1:eval=frame[h];
    [2:v]format=rgba,scale=w='210*min(1,max(0.01,(t-1)*5))':h=-1:eval=frame[b];
    [0:v]trim=0:5,setpts=PTS-STARTPTS[m];
    [m][h]overlay=x='480+15*sin(t*3)':y='40+10*cos(t*4)':enable='gte(t,0.3)':shortest=1[x];
    [x][b]overlay=x=60:y=50:enable='gte(t,1)':shortest=1[v];
    [3:a]adelay=1000|1000[p];[0:a]atrim=0:5[o];[o][p]amix=inputs=2:normalize=0[a]" \
    -map "[v]" -map "[a]" -t 5 $ENC $T/29.mp4
  finish $T/29.mp4 29_stickers "29 ステッカー合成"
}

demo_30() { # オープニングタイトル
  $FF -f lavfi -i "color=c=0xFFE4EC:s=640x360:r=24:d=5" -i $S/blink.mp4 -i $S/chime.wav -i $S/bgm.wav -filter_complex "
    [0:v]drawtext=$TXT:fontsize='min(64,(t*160))':fontcolor=0xE85A82:bordercolor=white:borderw=6:text='猫の愛情表現':x=(w-tw)/2:y=(h-th)/2-30,
      drawtext=$TXT:fontsize=24:fontcolor=0x7A4A5A:borderw=0:text='〜 動画編集デモ集 〜':x=(w-tw)/2:y=h/2+40:alpha='min(1,max(0,(t-0.7)*2))',
      drawbox=x=0:y=0:w='iw*min(1,t/1.2)':h=8:color=0xE85A82:t=fill,drawbox=x='iw-iw*min(1,t/1.2)':y=ih-8:w=iw:h=8:color=0xE85A82:t=fill,
      trim=0:2.6,format=yuv420p,settb=1/24[title];
    [1:v]trim=1.5:4.4,setpts=PTS-STARTPTS,fps=24,format=yuv420p,settb=1/24[clip];
    [title][clip]xfade=transition=circlecrop:duration=0.6:offset=2.0[v];
    [2:a]volume=0.8[c];[3:a]atrim=0:5,volume=0.5,afade=t=out:st=4.2:d=0.8[b];[b][c]amix=inputs=2:normalize=0[a]" \
    -map "[v]" -map "[a]" -t 5 $ENC $T/30.mp4
  finish $T/30.mp4 30_opening_title "30 オープニングタイトル"
}

demo_31() { # ループ GIF 書き出し
  $FF -i $S/knead.mp4 -vf "trim=0:2.7,setpts=PTS-STARTPTS,fps=12,scale=400:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
    -loop 0 "$O/31_loop.gif"
  echo "  -> $O/31_loop.gif"
}

ALL=$(declare -F | awk '{print $3}' | grep '^demo_' | sed 's/demo_//')
for n in ${@:-$ALL}; do echo "demo_$n"; demo_$n; done
[ -z "${KEEP_TMP:-}" ] && rm -rf "$T" || true
