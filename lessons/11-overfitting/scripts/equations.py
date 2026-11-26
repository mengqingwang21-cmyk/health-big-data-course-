"""Equations matching the implemented experiments; LaTeX for Word OMML."""
EQUATIONS = {
1:[r'z_{ij}=\frac{x_{ij}-\mu_j}{\sigma_j}',r'\mu_j=\frac{1}{n_T}\sum_{i\in T}x_{ij},\quad \sigma_j^2=\frac{1}{n_T}\sum_{i\in T}(x_{ij}-\mu_j)^2'],
2:[r'F_j=\frac{\sum_{c=0}^{1}n_c(\bar{x}_{cj}-\bar{x}_j)^2/(2-1)}{\sum_{c=0}^{1}\sum_{i:y_i=c}(x_{ij}-\bar{x}_{cj})^2/(n_T-2)}'],
3:[r'G(t)=1-\sum_{c=0}^{1}p_{tc}^2',r'\Delta G=G(t)-\frac{n_L}{n_t}G(L)-\frac{n_R}{n_t}G(R)'],
4:[r'\hat{p}_i=\frac{1}{1+\exp[-(\beta_0+\beta^{\mathsf{T}}z_i)]}'],
5:[r'\min_{\beta_0,\beta}J=\frac{1}{n_T}\sum_{i\in T}\left[-y_i\log\hat{p}_i-(1-y_i)\log(1-\hat{p}_i)\right]+\frac{\|\beta\|_2^2}{2Cn_T}'],
6:[r'i^*=\arg\min_{i\in T}\sqrt{\sum_j(x_j-x_{ij})^2},\quad \hat{p}(y=1\mid x)=y_{i^*}'],
7:[r'\mathrm{AUC}=\frac{1}{n_+n_-}\sum_{i:y_i=1}\sum_{j:y_j=0}\left[I(s_i>s_j)+\frac{1}{2} I(s_i=s_j)\right]'],
8:[r'\Delta_i=\frac{1}{171}\sum_{v=1}^{171}\left|\hat{p}_v^{(-i)}-\hat{p}_v^{(\mathrm{all})}\right|'],
9:[r'b^*(B)=\arg\max_{1\leq b\leq B}\mathrm{AUC}(y^H,s_b^H)',r'a^f(B)=\mathrm{AUC}(y^f,s_{b^*(B)}^f)'],
10:[r'x_d=y+\epsilon_d,\quad \epsilon_d\sim\mathcal{N}(0,1.2^2)',r'x_s=y+\epsilon_s\ (\mathrm{original}),\quad x_s=1-y+\epsilon_s\ (\mathrm{new})',r'\epsilon_s\sim\mathcal{N}(0,0.2^2)']
}
