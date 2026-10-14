"""Build precise, lightweight teaching diagrams (no formulas or solution code)."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tutorial/static/images/tasks'
root.mkdir(parents=True,exist_ok=True)
style='<style>text{font:16px sans-serif;fill:#34556f} .line{fill:none;stroke:#5789b0;stroke-width:3} .fill{fill:#e7f1f8;stroke:#5789b0;stroke-width:2}</style>'
def save(name,body):
 (root/(name+'.svg')).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 220">'+style+body+'</svg>')
save('triangle','<path class="fill" d="M110 30V180H370Z"/><path class="line" d="M110 160h20v20"/><text x="82" y="110">a</text><text x="236" y="206">b</text><text x="258" y="88">c</text><text x="143" y="168">90°</text>')
body='<rect class="fill" x="36" y="14" width="408" height="160" rx="18"/><rect x="58" y="36" width="364" height="110" rx="10" fill="#f7fafc"/><text x="104" y="110" style="font-size:38px">часы : минуты</text><text x="104" y="199">0–23</text><text x="294" y="199">0–59</text>'
save('digital-clock',body)
body='<circle class="fill" cx="240" cy="105" r="86"/><text x="230" y="43">12</text><text x="307" y="111">3</text><text x="235" y="180">6</text><text x="164" y="111">9</text><path d="M240 105V50" stroke="#bccfdd" stroke-width="2" stroke-dasharray="4 4"/><path class="line" d="M240 105L285 73"/><path d="M240 67A38 38 0 0 1 271 83" class="line"/><circle cx="240" cy="105" r="5" fill="#34556f"/><text x="252" y="61">α</text><text x="167" y="214">Часовая стрелка</text>'
save('clock',body)
body='<ellipse class="fill" cx="240" cy="106" rx="152" ry="74"/><ellipse cx="240" cy="106" rx="130" ry="54" fill="white"/><circle cx="240" cy="33" r="6" fill="#34556f"/><text x="214" y="20">0 км</text><text x="201" y="110">109 км</text><path class="line" d="M398 77Q419 118 388 146"/><path d="m385 133 3 13 15-2" class="line"/><text x="400" y="166">+v</text><text x="93" y="207">Движение по кольцу от отметки 0</text>'
save('ring-road',body)
body=''
for x in range(6):
 for y in range(3):body+=f'<rect x="{100+x*42}" y="{35+y*42}" width="40" height="40" fill="'+('#b7d3e6' if x<2 else '#edf4f8')+'" stroke="#5789b0"/>'
body+='<path d="M183 20V178" stroke="#d48054" stroke-width="3" stroke-dasharray="6 4"/><text x="204" y="18">m столбцов</text><text x="16" y="100">n рядов</text><text x="100" y="206">Пример прямого разлома</text>'
save('chocolate',body)
body='<path class="fill" d="M175 50h130l-15 60h-100Z"/>'
for x in [200,225,250,275]:body+=f'<circle cx="{x}" cy="43" r="13" fill="#a5c8df" stroke="#5789b0"/><path d="M{x} 30q6-10 11-7" class="line"/>'
for x in [120,240,360]:body+=f'<circle class="fill" cx="{x}" cy="155" r="16"/><path class="line" d="M{x-25} 205q0-35 25-35t25 35"/>'
body+='<text x="18" y="28">k яблок</text><text x="326" y="132">n школьников</text>'
save('apples',body)
body=''
for i,label in enumerate(['Класс 1','Класс 2','Класс 3']):
 x=30+i*153
 body+=f'<text x="{x+13}" y="35">{label}</text><rect class="fill" x="{x}" y="110" width="112" height="45" rx="5"/><path class="line" d="M{x+12} 155v35m88-35v35"/>'
 for dx in [28,82]:body+=f'<circle class="fill" cx="{x+dx}" cy="80" r="16"/>'
body+='<text x="151" y="213">Два места за партой</text>'
save('desks',body)
body=''
for col in range(8):
 for row in range(8):body+=f'<rect x="{135+col*22}" y="{16+row*22}" width="22" height="22" fill="'+('#9cbcd3' if (col+row)%2==0 else '#eef5fa')+'"/>'
for n in range(8):body+=f'<text x="{141+n*22}" y="212" style="font-size:12px">{n+1}</text><text x="116" y="{31+n*22}" style="font-size:12px">{8-n}</text>'
body+='<circle cx="212" cy="115" r="7" fill="#34556f"/><text x="329" y="115">(4, 4)</text><path d="M222 115h100" class="line"/><text x="327" y="139" style="font-size:12px">столбец, строка</text>'
save('chess-coordinates',body)
