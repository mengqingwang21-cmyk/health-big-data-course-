from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from equations import EQUATIONS
B=Path(__file__).resolve().parents[1]
out=B/'results'/'equations'; out.mkdir(exist_ok=True)
for num,lines in EQUATIONS.items():
    for idx,line in enumerate(lines):
        fig=plt.figure(figsize=(10,.7),dpi=240)
        fig.text(.01,.5,'$'+line+'$',fontsize=15,ha='left',va='center')
        fig.savefig(out/f'eq-{num}-{idx}.png',dpi=240,bbox_inches='tight',pad_inches=.07,facecolor='white')
        plt.close(fig)
print('Rendered equation lines.')
