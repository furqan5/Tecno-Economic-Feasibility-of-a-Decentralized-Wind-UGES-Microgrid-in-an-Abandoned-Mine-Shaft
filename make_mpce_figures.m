%% ========================================================================
%  make_mpce_figures.m   (v6 - reads figure_data/*.csv; single source of truth)
%  Figures 3-7 for the Jhimpir Wind-UGES manuscript. MPCE / IEEE two-column.
%
%  DATA FLOW (option C):  the Python package writes figure_data/*.csv when run
%  (python run_simulation.py); this script only READS those CSVs and renders.
%  Figures therefore cannot drift from the numerical results.
%
%  Requirements: MATLAB R2020a+ (readtable, tiledlayout, yyaxis, exportgraphics).
%  Place this file in the repository root (next to the figure_data/ folder).
%  Run the top cell once, then Ctrl+Enter any figure cell.
%  ------------------------------------------------------------------------
%  Fig-3 note: figure_data/fig3_settlement.csv currently holds a REPRESENTATIVE
%  settlement bowl anchored to the PLAXIS 3D maximum. Overwrite its two columns
%  with the PLAXIS settlement path for the final figure (peak label auto-updates).
%  ========================================================================
clear; close all; clc;

% ---- locate the data folder (next to this script) ----------------------
here = fileparts(mfilename('fullpath'));
if isempty(here), here = pwd; end
DATA_DIR = fullfile(here,'figure_data');
assert(isfolder(DATA_DIR), ...
    'figure_data/ not found. Run "python run_simulation.py" first, or set DATA_DIR.');

% ---- shared style ------------------------------------------------------
FONT = 'Times New Roman';          % change to 'Arial' for a sans layout
FS   = 11;
set(groot, ...
    'defaultAxesFontName',FONT,'defaultTextFontName',FONT, ...
    'defaultAxesFontSize',FS,  'defaultAxesFontWeight','bold', ...
    'defaultTextFontWeight','bold','defaultLegendFontSize',FS-1, ...
    'defaultAxesLineWidth',1.0,'defaultLineLineWidth',1.8, ...
    'defaultAxesTickDir','out','defaultAxesTickLength',[0.02 0.02], ...
    'defaultAxesXColor',[.1 .1 .1],'defaultAxesYColor',[.1 .1 .1], ...
    'defaultFigureColor','w');

C.blue  =[  0 114 178]/255;  C.verm =[213  94   0]/255;
C.green =[  0 158 115]/255;  C.orange=[230 159   0]/255;
C.sky   =[ 86 180 233]/255;  C.purple=[204 121 167]/255;
C.grey  =[ 70  70  70]/255;
W1 = 8.9;  W2 = 18.2;                 % cm: single / double column
save(fullfile(here,'mpce_style.mat'),'C','W1','W2','FONT','FS','DATA_DIR');
fprintf('Style loaded. Data: %s\n', DATA_DIR);


%% ===== FIG 3 - Headframe foundation settlement bowl =====================
load(fullfile(fileparts(mfilename('fullpath')),'mpce_style.mat'));
T = readtable(fullfile(DATA_DIR,'fig3_settlement.csv'));
x = T.distance_m;  s = T.settlement_mm;
S_MAX  = max(s);   S_CODE = 25.0;                % code allowable is a fixed value
[~,ipk] = max(s);  xpk = x(ipk);

fig = figure('Units','centimeters','Position',[2 2 W1 7.4]);
tl  = tiledlayout(fig,1,1,'Padding','compact'); ax = nexttile(tl);
hold(ax,'on'); box(ax,'off');
fill(ax,[x; flipud(x)],[s; zeros(size(s))],C.blue,'FaceAlpha',.10,'EdgeColor','none');
plot(ax,x,s,'-','Color',C.blue,'LineWidth',2.4);
yline(ax,S_CODE,':','Code allowable, 25 mm','Color',C.grey,'LineWidth',1.4, ...
      'FontName',FONT,'FontSize',FS-1,'FontWeight','bold', ...
      'LabelHorizontalAlignment','left','LabelVerticalAlignment','top');
plot(ax,xpk,S_MAX,'o','MarkerFaceColor',C.green,'MarkerEdgeColor','w', ...
     'MarkerSize',8,'LineWidth',1.0);
plot(ax,[xpk xpk+2.3],[S_MAX 21],'-','Color',C.grey,'LineWidth',0.7);
text(ax,xpk+2.5,21.2,sprintf('Peak %.2f mm (PLAXIS 3D)',S_MAX), ...
     'Color',C.green*0.75,'FontSize',FS-1,'FontWeight','bold', ...
     'HorizontalAlignment','left','VerticalAlignment','top');
set(ax,'YDir','reverse','YLim',[0 27],'XLim',[0 max(x)]);
ax.YGrid='on'; ax.GridLineStyle=':'; ax.GridAlpha=.3;
xlabel(ax,'Distance from footing centre (m)','FontWeight','bold');
ylabel(ax,'Surface settlement (mm)','FontWeight','bold');
drawnow; exp_fig(tl,'fig3_settlement.tiff');


%% ===== FIG 4 - Load-flow steady state (double column, 3 panels) ========
load(fullfile(fileparts(mfilename('fullpath')),'mpce_style.mat'));
T = readtable(fullfile(DATA_DIR,'fig4_loadflow.csv'));
st = string(T.state);                            % Charging / Discharging
xp = 1:height(T);  bcol = [C.blue; C.verm];

fig = figure('Units','centimeters','Position',[2 2 W2 6.8]);
tl  = tiledlayout(fig,1,3,'TileSpacing','compact','Padding','compact');

ax = nexttile(tl);
b=bar(ax,xp,T.export_MW,.55,'FaceColor','flat'); b.CData=bcol; b.EdgeColor='none';
barlab(ax,xp,T.export_MW,'%.1f',FS);
set(ax,'XTick',xp,'XTickLabel',st); xlim(ax,[.4 xp(end)+.7]); ylim(ax,[0 66]);
ylabel(ax,'Net export to 132 kV grid (MW)','FontWeight','bold'); grid_y(ax);
title(ax,'(a)','FontWeight','bold');

ax = nexttile(tl);
b=bar(ax,xp,T.pcc_pct,.55,'FaceColor','flat'); b.CData=bcol; b.EdgeColor='none';
yline(ax,105,'--','+5%','Color',C.grey,'LineWidth',1.2,'FontName',FONT,'FontSize',FS-2, ...
      'FontWeight','bold','LabelHorizontalAlignment','right','LabelVerticalAlignment','bottom');
yline(ax, 95,'--','-5%','Color',C.grey,'LineWidth',1.2,'FontName',FONT,'FontSize',FS-2, ...
      'FontWeight','bold','LabelHorizontalAlignment','right','LabelVerticalAlignment','top');
barlab(ax,xp,T.pcc_pct,'%.1f',FS);
set(ax,'XTick',xp,'XTickLabel',st); xlim(ax,[.4 xp(end)+.7]); ylim(ax,[90 110]);
ylabel(ax,'PCC voltage (% nominal)','FontWeight','bold'); grid_y(ax);
title(ax,'(b)','FontWeight','bold');

ax = nexttile(tl);
b=bar(ax,xp,T.xfmr_pct,.55,'FaceColor','flat'); b.CData=bcol; b.EdgeColor='none';
yline(ax,100,'--','rated','Color',C.grey,'LineWidth',1.2,'FontName',FONT,'FontSize',FS-2, ...
      'FontWeight','bold','LabelHorizontalAlignment','right','LabelVerticalAlignment','bottom');
barlab(ax,xp,T.xfmr_pct,'%.1f',FS);
set(ax,'XTick',xp,'XTickLabel',st); xlim(ax,[.4 xp(end)+.7]); ylim(ax,[0 120]);
ylabel(ax,'63 MVA transformer loading (%)','FontWeight','bold'); grid_y(ax);
title(ax,'(c)','FontWeight','bold');
drawnow; exp_fig(tl,'fig4_loadflow.tiff');


%% ===== FIG 5 - EMS 24-h dispatch (dual axis, legend below) =============
load(fullfile(fileparts(mfilename('fullpath')),'mpce_style.mat'));
T = readtable(fullfile(DATA_DIR,'fig5_ems.csv'));
h = T.hour;  P = T.P_MW;  SOC = T.SOC_pct;  tariff = T.tariff_PKR;

fig = figure('Units','centimeters','Position',[2 2 W1 8.6]);
tl  = tiledlayout(fig,1,1,'Padding','compact'); ax = nexttile(tl);
yyaxis(ax,'left');
pos=P; pos(P<0)=NaN;  neg=P; neg(P>=0)=NaN;
b1=bar(ax,h,pos,.75,'FaceColor',C.green,'EdgeColor','none'); hold(ax,'on');
b2=bar(ax,h,neg,.75,'FaceColor',C.verm ,'EdgeColor','none');
ylabel(ax,'UGES power (MW):  + dis / - chg','FontWeight','bold');
ylim(ax,[-1.2 1.2]); ax.YColor=[.1 .1 .1];
yyaxis(ax,'right');
p1=plot(ax,h,SOC,'-o','Color',C.blue,'MarkerFaceColor',C.blue,'MarkerSize',5,'LineWidth',2.0);
p2=plot(ax,h,tariff,'--','Color',C.orange,'LineWidth',2.0);
ylabel(ax,'SOC (%)   /   tariff (PKR/kWh)','FontWeight','bold');
ylim(ax,[0 100]); ax.YColor=[.1 .1 .1];
xlim(ax,[-.6 23.6]); xticks(ax,0:4:23);
xlabel(ax,'Hour of day','FontWeight','bold');
ax.XGrid='on'; ax.GridLineStyle=':'; ax.GridAlpha=.28;
lg = legend(ax,[b1 b2 p1 p2],{'discharge','charge','SOC','tariff'});
lg.NumColumns=2; lg.Box='off'; lg.Layout.Tile='south';
lg.FontWeight='bold'; lg.FontSize=FS-1;
drawnow; exp_fig(tl,'fig5_ems.tiff');


%% ===== FIG 6 - Factors of safety vs code minima (log axis) =============
load(fullfile(fileparts(mfilename('fullpath')),'mpce_style.mat'));
T = readtable(fullfile(DATA_DIR,'fig6_structural.csv'));
lbl = string(T.component);  fos = T.fos;  fmin = T.fos_min;

fig = figure('Units','centimeters','Position',[2 2 W1 7.0]);
tl  = tiledlayout(fig,1,1,'Padding','compact'); ax = nexttile(tl);
hold(ax,'on'); box(ax,'off');
y = 1:numel(fos);
hb = barh(ax,y,fos,.55,'FaceColor',C.blue,'EdgeColor','none');
for k = 1:numel(fos)
    plot(ax,[fmin(k) fmin(k)],[y(k)-.36 y(k)+.36],'Color',C.verm,'LineWidth',2.6);
    text(ax,fos(k)*1.22,y(k),sprintf('%g',fos(k)), ...
         'VerticalAlignment','middle','FontSize',FS,'FontWeight','bold');
end
hmin = plot(ax,NaN,NaN,'Color',C.verm,'LineWidth',2.6);
set(ax,'XScale','log','XLim',[1 4000],'YLim',[.4 numel(fos)+.6], ...
       'YTick',y,'YTickLabel',lbl,'YDir','reverse');
ax.XGrid='on'; ax.GridLineStyle=':'; ax.GridAlpha=.3;
ax.XMinorGrid='on'; ax.MinorGridLineStyle=':'; ax.MinorGridAlpha=.12;
xlabel(ax,'Factor of safety (log scale)','FontWeight','bold');
lg = legend([hb hmin],{'achieved','code / design min'});
lg.Location='northeast'; lg.Box='off'; lg.FontWeight='bold'; lg.FontSize=FS-1;
drawnow; exp_fig(tl,'fig6_structural.tiff');


%% ===== FIG 7 - Resilience (survivability + islanding) ==================
load(fullfile(fileparts(mfilename('fullpath')),'mpce_style.mat'));
Ta = readtable(fullfile(DATA_DIR,'fig7a_survivability.csv'));
Tb = readtable(fullfile(DATA_DIR,'fig7b_islanding.csv'));
[~,ord] = sort(Tb.P72_pct,'ascend'); Tb = Tb(ord,:);      % worst -> best

fig = figure('Units','centimeters','Position',[2 2 W1 14.5]);
tl  = tiledlayout(fig,2,1,'TileSpacing','compact','Padding','compact');

ax = nexttile(tl); hold(ax,'on'); box(ax,'off');
h1=plot(ax,Ta.M,Ta.AG1,'--o','Color',C.verm ,'MarkerFaceColor',C.verm ,'MarkerSize',5,'LineWidth',1.8);
h2=plot(ax,Ta.M,Ta.AG5,'--s','Color',C.orange,'MarkerFaceColor',C.orange,'MarkerSize',5,'LineWidth',1.8);
h3=plot(ax,Ta.M,Ta.UG1,'-o' ,'Color',C.blue ,'MarkerFaceColor',C.blue ,'MarkerSize',5,'LineWidth',1.8);
h4=plot(ax,Ta.M,Ta.UG5,'-s' ,'Color',C.green,'MarkerFaceColor',C.green,'MarkerSize',5,'LineWidth',1.8);
xlabel(ax,'Salvo size, M (independent strikes)','FontWeight','bold');
ylabel(ax,'Surviving inventory (%)','FontWeight','bold');
xlim(ax,[0 max(Ta.M)]); ylim(ax,[0 102]); xticks(ax,0:2:max(Ta.M)); grid_y(ax);
title(ax,'(a)  strike survivability  (p_{AG}=0.8, p_{sh}=0.05)','FontWeight','bold');
lg = legend(ax,[h1 h2 h3 h4], ...
     {'AG-BESS, single','AG-BESS, 5 nodes','UGES, single','UGES, 5 shafts'});
lg.Location='northoutside'; lg.NumColumns=2; lg.Box='off'; lg.FontWeight='bold'; lg.FontSize=FS-1;

ax = nexttile(tl);
% shorten long load names for the tick labels; full names live in the caption
nm = string(Tb.load);
nm = replace(nm,"Hospital, full critical","Hospital (full)");
nm = replace(nm,"Hospital, shed core","Hospital (shed)");
nm = replace(nm,"Forward operating base","Forward base");
cats = categorical(nm, nm);                      % preserve worst->best order
P72 = Tb.P72_pct;  buf = Tb.buffer_h;
bcol = [C.verm; C.orange; C.purple; C.green];
bcol = bcol(1:numel(P72),:);
b = barh(ax,cats,P72,.6,'FaceColor','flat'); b.CData=bcol; b.EdgeColor='none';
for k = 1:numel(P72)
    text(ax,max(P72(k),1)+3,k,sprintf('%.1f%%  (%.1f h)',P72(k),buf(k)), ...
         'VerticalAlignment','middle','FontSize',FS-1,'FontWeight','bold');
end
xlim(ax,[0 150]); xlabel(ax,'P(72 h uninterrupted islanded supply) (%)','FontWeight','bold');
ax.XGrid='on'; ax.GridLineStyle=':'; ax.GridAlpha=.3;
title(ax,'(b)  islanding endurance, 1.083 MWh + 2.5 MW turbine','FontWeight','bold');
drawnow; exp_fig(tl,'fig7_resilience.tiff');

fprintf('All figures written as 300-dpi TIFF (LZW).\n');


%% ===== local helpers ===================================================
function exp_fig(obj,name)
    if exist('exportgraphics','file')
        exportgraphics(obj,name,'Resolution',300,'ContentType','image');
    else
        print(ancestor(obj,'figure'),name,'-dtiff','-r300');   %#ok<PRTCAL>
    end
end
function barlab(ax,xp,vals,fmt,fs)
    for k = 1:numel(vals)
        text(ax,xp(k),vals(k),sprintf(fmt,vals(k)),'HorizontalAlignment','center', ...
             'VerticalAlignment','bottom','FontSize',fs,'FontWeight','bold');
    end
end
function grid_y(ax)
    ax.YGrid='on'; ax.GridLineStyle=':'; ax.GridAlpha=.3; box(ax,'off');
end
