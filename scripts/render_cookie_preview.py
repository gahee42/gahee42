"""Render the profile's gently rocking cookie GIF. Requires Pillow; --font accepts a Korean font."""
from pathlib import Path
import argparse
import math
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--font', type=Path)
args = parser.parse_args()
font_path = args.font or next((p for p in (
    Path('/System/Library/Fonts/AppleSDGothicNeo.ttc'),
    Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
    Path('C:/Windows/Fonts/malgun.ttf'),
) if p.exists()), None)
if not font_path:
    parser.error('Use --font to select a Korean font.')
S = 2
size = (260*S, 310*S)
def font(px, bold=False):
    index = 6 if bold and font_path.name == "AppleSDGothicNeo.ttc" else 0
    return ImageFont.truetype(str(font_path), round(px*S), index=index)
def box(coords): return tuple(round(v*S) for v in coords)
def text(draw, xy, value, px, fill, anchor='mm', bold=False):
    draw.text((round(xy[0]*S), round(xy[1]*S)), value, font=font(px, bold), fill=fill, anchor=anchor)
def star(draw, x, y, radius, fill):
    points=[]
    for i in range(8):
        angle=i*math.pi/4
        r=radius if i%2==0 else radius*.25
        points.append(((x+math.cos(angle)*r)*S,(y+math.sin(angle)*r)*S))
    draw.polygon(points,fill=fill)

background=Image.new('RGBA',size,'#fffef6')
d=ImageDraw.Draw(background)
d.rounded_rectangle(box((1,1,259,309)),radius=18*S,outline='#dce6d7',width=S)
d.rounded_rectangle(box((7,7,253,303)),radius=14*S,outline='#edf0e2',width=S)
text(d,(130,25),'F O R T U N E  C L U B',9,'#688068')
text(d,(117,53),'오늘의 운세는',22,'#34513f',bold=True)
text(d,(210,49),'두근!',11,'#7c9464')
d.ellipse(box((52,78,208,234)),fill='#f2f4dc',outline='#e6eccb',width=S)
d.rounded_rectangle(box((67,245,193,280)),radius=9*S,fill='#92b997')
d.rounded_rectangle(box((67,242,193,276)),radius=9*S,fill='#c8e3c6',outline='#b5d3b4',width=S)
text(d,(130,259),'쿠키 뽑기  ↗',13,'#34513f',bold=True)
text(d,(130,292),'눌러서 작은 행운 만나기',10,'#7b896f')
cookie=Image.open(ROOT/'docs/fortune-cookie-illustrated.png').convert('RGBA')
cookie.thumbnail((204*S,204*S),Image.Resampling.LANCZOS)
frames=[]
# A brief, eased handling gesture followed by a calm pause. No automatic cracking.
frame_count=40
for i in range(frame_count):
    t=i/(frame_count-1)
    envelope=math.sin(math.pi*t)**2
    angle=3.2*math.sin(4*math.pi*t)*envelope
    bob=-3.0*envelope
    if i in (0,frame_count-1):
        angle=bob=envelope=0
    frame=background.copy()
    rotated=cookie.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
    frame.alpha_composite(rotated,(round(130*S-rotated.width/2),round((155+bob)*S-rotated.height/2)))
    draw=ImageDraw.Draw(frame)
    star(draw,31,141,5+.6*envelope,'#94ae89')
    star(draw,229,190,5+.8*envelope,'#b7a35d')
    frames.append(frame.convert('RGB'))
assert ImageChops.difference(frames[0],frames[-1]).getbbox() is None
# A shared palette prevents color shimmer between animation frames.
palette=frames[0].quantize(colors=192,method=Image.Quantize.MEDIANCUT)
indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
durations=[50]*frame_count
durations[-1]=1800
out=ROOT/'assets/fortune-cookie-preview.gif'
indexed[0].save(out,save_all=True,append_images=indexed[1:],duration=durations,loop=0,optimize=True,disposal=1)
frames[0].save('/tmp/fortune-cookie-preview-still.png')
with Image.open(out) as gif:
    count=gif.n_frames
    total=sum((gif.seek(i),gif.info.get('duration',0))[1] for i in range(count))
    assert gif.size==size and count>1 and gif.info.get('loop')==0
print(f'{out.name}: {out.stat().st_size:,} bytes, {count} frames, {total}ms loop, {size[0]}x{size[1]}')
