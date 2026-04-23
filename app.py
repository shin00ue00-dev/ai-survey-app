"""
AI世論調査 全自動生成システム v3
- 文字化け修正（システムフォント使用）
- 生成履歴の保存・一覧
- テーマ重複チェック
- グラフPNG・ZIP出力
"""

import re, io, zipfile, json, os, datetime
import numpy as np
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from anthropic import Anthropic

def get_jp_font():
    candidates = [
        "Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "IPAPGothic",
        "VL Gothic", "Hiragino Sans", "Yu Gothic", "MS Gothic", "DejaVu Sans",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for c in candidates:
        if c in available:
            return c
    return "DejaVu Sans"

JP_FONT = get_jp_font()
plt.rcParams["font.family"] = JP_FONT
plt.rcParams["axes.unicode_minus"] = False

HISTORY_FILE = "/tmp/survey_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_to_history(record):
    history = load_history()
    history.insert(0, record)
    history = history[:50]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_past_themes():
    return [h.get("theme_key", "") for h in load_history()]

st.set_page_config(page_title="AI世論調査 全自動生成システム", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:1.5rem;}
.stButton>button{width:100%;background:#2B4C9B;color:#fff;border:none;border-radius:8px;padding:12px;font-size:15px;font-weight:600;}
.stButton>button:hover{background:#1e3a7a;color:#fff;}
section[data-testid="stSidebar"]{min-width:270px;}
.history-card{background:#f8f9fd;border-radius:8px;padding:10px 14px;margin-bottom:8px;border-left:3px solid #2B4C9B;font-size:13px;}
</style>
""", unsafe_allow_html=True)

BG="#0d1020"; TEXT_C="#ffffff"; SUBTEXT="#aabbdd"
BLUES=["#2B4C9B","#4a7fd4","#7B9FE0","#B5D4F4","#dce9f8","#a0b8e8","#6080c0","#3a5aaa","#8090d0","#c0d0f0"]
GCOL={"M":"#4a7fd4","F":"#e05c8a"}
AGES_JP=["20代","30代","40代","50代以上"]
AGECOL=["#2B4C9B","#4a7fd4","#7B9FE0","#B5D4F4"]

def _style():
    plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":BG,"axes.edgecolor":"#334466","axes.labelcolor":TEXT_C,"xtick.color":SUBTEXT,"ytick.color":TEXT_C,"text.color":TEXT_C,"grid.color":"#223355","grid.alpha":0.5,"font.family":JP_FONT})

def _note(fig):
    fig.text(0.98,0.01,"※AIシミュレーション",ha="right",fontsize=8,color="#556688")

def _save(fig):
    buf=io.BytesIO(); fig.savefig(buf,dpi=150,bbox_inches="tight",facecolor=BG); plt.close(fig); return buf.getvalue()

def make_all_graphs(ranking,title,n_sample):
    _style()
    top_n=min(len(ranking),10); labels=[r["label"] for r in ranking[:top_n]]; pcts=[r["pct"] for r in ranking[:top_n]]; colors=BLUES[:top_n]; graphs={}
    short_title=title[:22]+"…" if len(title)>22 else title; caption=f"AIシミュレーション n={n_sample:,}人"

    fig,ax=plt.subplots(figsize=(9,5.5)); y=np.arange(top_n)[::-1]
    ax.barh(y,pcts,color=colors,height=0.55,zorder=3)
    medal_c=["#FFD700","#C0C0C0","#CD7F32"]+[SUBTEXT]*(top_n-3)
    for i,(bar,val) in enumerate(zip(ax.patches,pcts)):
        ax.text(val+0.8,bar.get_y()+bar.get_height()/2,f"{val}%",va="center",ha="left",fontsize=12,fontweight="bold")
        ax.text(-1.2,bar.get_y()+bar.get_height()/2,f"{ranking[i]['rank']}位",va="center",ha="right",fontsize=10,color=medal_c[i])
    ax.set_yticks(y); ax.set_yticklabels(labels[::-1],fontsize=11); ax.set_xlim(-6,max(pcts)+14); ax.grid(axis="x",zorder=0); ax.spines[:].set_visible(False)
    ax.set_title(f"{short_title}\n({caption})",fontsize=13,fontweight="bold",pad=14); _note(fig); plt.tight_layout()
    graphs["graph_01_overall.png"]=_save(fig)

    top5=labels[:5]; top5p=pcts[:5]; rng=np.random.default_rng(42)
    age_data={a:[max(0,min(100,v+rng.integers(-12,13))) for v in top5p] for a in AGES_JP}
    fig,ax=plt.subplots(figsize=(10,5.5)); x=np.arange(len(top5)); w=0.18
    for i,(age,vals) in enumerate(age_data.items()):
        offs=(-1.5+i)*w; bs=ax.bar(x+offs,vals,w*0.9,label=age,color=AGECOL[i],zorder=3)
        for b,v in zip(bs,vals): ax.text(b.get_x()+b.get_width()/2,b.get_height()+0.6,str(v),ha="center",fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(top5,fontsize=10); ax.set_ylim(0,95); ax.grid(axis="y",zorder=0); ax.spines[:].set_visible(False)
    ax.legend(fontsize=10,framealpha=0.15,facecolor="#1a2a4a",labelcolor=TEXT_C)
    ax.set_title(f"年代別｜{short_title}\n({caption})",fontsize=12,fontweight="bold",pad=14); _note(fig); plt.tight_layout()
    graphs["graph_02_age.png"]=_save(fig)

    rng2=np.random.default_rng(7); mv=[max(0,min(100,v+rng2.integers(-10,8))) for v in top5p]; fv=[max(0,min(100,v+rng2.integers(-8,12))) for v in top5p]
    fig,ax=plt.subplots(figsize=(9,5.5)); yy=np.arange(len(top5)); ww=0.36
    ax.barh(yy+ww/2,mv,ww*0.9,label="男性",color=GCOL["M"],zorder=3); ax.barh(yy-ww/2,fv,ww*0.9,label="女性",color=GCOL["F"],zorder=3)
    for i,(m,f) in enumerate(zip(mv,fv)):
        ax.text(m+0.6,yy[i]+ww/2,f"{m}%",va="center",fontsize=10); ax.text(f+0.6,yy[i]-ww/2,f"{f}%",va="center",fontsize=10)
    ax.set_yticks(yy); ax.set_yticklabels(top5,fontsize=11); ax.set_xlim(0,max(mv+fv)+16); ax.grid(axis="x",zorder=0); ax.spines[:].set_visible(False)
    ax.legend(fontsize=11,framealpha=0.15,facecolor="#1a2a4a",labelcolor=TEXT_C)
    ax.set_title(f"性別比較｜{short_title}\n({caption})",fontsize=12,fontweight="bold",pad=14); _note(fig); plt.tight_layout()
    graphs["graph_03_gender.png"]=_save(fig)

    base=pcts[0]; rng3=np.random.default_rng(13)
    m_c=[max(0,min(100,base+rng3.integers(-15,5))) for _ in AGES_JP]; f_c=[max(0,min(100,base+rng3.integers(-5,15))) for _ in AGES_JP]
    fig,ax=plt.subplots(figsize=(9,4.5)); xx=np.arange(len(AGES_JP)); wc=0.35
    bm=ax.bar(xx-wc/2,m_c,wc*0.9,label="男性",color=GCOL["M"],zorder=3); bf=ax.bar(xx+wc/2,f_c,wc*0.9,label="女性",color=GCOL["F"],zorder=3)
    for b,v in zip(bm,m_c): ax.text(b.get_x()+b.get_width()/2,b.get_height()+0.8,f"{v}%",ha="center",fontsize=11,fontweight="bold")
    for b,v in zip(bf,f_c): ax.text(b.get_x()+b.get_width()/2,b.get_height()+0.8,f"{v}%",ha="center",fontsize=11,fontweight="bold")
    ax.set_xticks(xx); ax.set_xticklabels(AGES_JP,fontsize=12); ax.set_ylim(0,max(m_c+f_c)+16); ax.grid(axis="y",zorder=0); ax.spines[:].set_visible(False)
    ax.legend(fontsize=11,framealpha=0.15,facecolor="#1a2a4a",labelcolor=TEXT_C)
    ax.set_title(f"クロス集計｜1位「{labels[0]}」\n({caption})",fontsize=12,fontweight="bold",pad=14); _note(fig); plt.tight_layout()
    graphs["graph_04_cross.png"]=_save(fig)

    fig=plt.figure(figsize=(5,9)); fig.patch.set_facecolor(BG); ax=fig.add_axes([0.18,0.08,0.76,0.68]); ax.set_facecolor(BG)
    yv=np.arange(min(5,top_n))[::-1]
    for i,(yi,val,col) in enumerate(zip(yv,pcts[:5],colors[:5])):
        ax.barh(yi,val,color=col,height=0.58,zorder=3); ax.text(val+0.8,yi,f"{val}%",va="center",fontsize=13,fontweight="bold"); ax.text(-0.5,yi,labels[i],va="center",ha="right",fontsize=9)
    ax.set_xlim(-20,max(pcts[:5])+18); ax.set_yticks([]); ax.grid(axis="x",zorder=0,alpha=0.3); ax.spines[:].set_visible(False)
    fig.text(0.5,0.91,short_title,ha="center",fontsize=16,fontweight="bold"); fig.text(0.5,0.96,caption,ha="center",fontsize=10,color="#7B9FE0")
    fig.text(0.5,0.02,"※AIシミュレーション",ha="center",fontsize=8,color="#556688")
    graphs["graph_05_vertical.png"]=_save(fig)
    return graphs

def make_zip(graphs):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w") as zf:
        for name,data in graphs.items(): zf.writestr(name,data)
    return buf.getvalue()

def ask(client,prompt):
    msg=client.messages.create(model="claude-opus-4-6",max_tokens=1500,messages=[{"role":"user","content":prompt}])
    return msg.content[0].text

def parse_ranking(text):
    items=[]
    for line in text.split("\n"):
        m=re.match(r'(\d+)位[：:]\s*(.+?)\s*[\/／]\s*支持率\s*(\d+)%',line)
        if m: items.append({"rank":int(m[1]),"label":m[2].strip(),"pct":int(m[3])})
    return items

with st.sidebar:
    st.markdown("## ⚙️ テーマ設定")
    api_key=st.text_input("Anthropic APIキー",type="password",placeholder="sk-ant-...")
    genre=st.selectbox("ジャンル",["ライフスタイル","お金・副業","恋愛・人間関係","仕事・キャリア","エンタメ・雑学"])
    keyword=st.text_input("キーワード",placeholder="例：節約、転職、推し活")
    target=st.selectbox("ターゲット視聴者",["20代全般","30代会社員","子育て世代","フリーランス・副業志望","シニア層"],index=2)
    top_n=st.radio("ランキング形式",["TOP5","TOP10"],horizontal=True)
    top_n_int=int(top_n.replace("TOP",""))
    n_size=st.select_slider("サンプル規模",options=[1000,3000,5000,10000],value=10000,format_func=lambda x:f"{x:,}人")
    theme_key=f"{genre}_{keyword}_{target}"
    if theme_key in get_past_themes():
        st.warning("⚠️ このテーマは過去に生成済みです。キーワードを変えると新鮮なコンテンツになります。")
    run=st.button("▶ 全自動生成スタート",use_container_width=True)
    st.divider()
    st.markdown("### 📂 生成履歴")
    history=load_history()
    if not history:
        st.caption("まだ履歴がありません")
    else:
        for h in history[:5]:
            st.markdown(f"<div class='history-card'><b>{h.get('title','')}</b><br><span style='color:#888;font-size:11px;'>{h.get('date','')} ／ {h.get('genre','')} ／ {h.get('target','')}</span></div>",unsafe_allow_html=True)

st.title("📊 AI世論調査 全自動生成システム")
st.caption("テーマ入力 → ランキング生成 → クロス集計 → グラフPNG → 原稿　をワンクリックで一括出力")

if not run:
    st.info("左のサイドバーでテーマを設定して「全自動生成スタート」を押してください。")
    if history:
        st.subheader("最近の生成")
        cols=st.columns(min(3,len(history)))
        for i,h in enumerate(history[:3]):
            with cols[i]: st.markdown(f"**{h.get('title','')}**"); st.caption(f"{h.get('date','')} ／ {h.get('genre','')}")
    st.stop()

if not api_key:
    st.error("APIキーを入力してください（サイドバー）"); st.stop()

client=Anthropic(api_key=api_key)

with st.status("**Step 1｜ランキング生成中...**",expanded=True) as status:
    try:
        rank_raw=ask(client,f"ジャンル「{genre}」、キーワード「{keyword or 'なし'}」、ターゲット「{target}」のTOP{top_n_int}ランキングを作成してください。\nWeb上のトレンド・統計を参考にしたAIシミュレーションとして出力してください。\n\n必ずこの形式で：\n【タイトル】キャッチーな動画タイトル一文\n【ランキング】\n"+"\n".join([f"{i+1}位: 項目名 / 支持率XX%" for i in range(top_n_int)])+"\n【コメント】各順位に共感できる一言")
        title_m=re.search(r'【タイトル】\s*(.+)',rank_raw); video_title=title_m.group(1).strip() if title_m else f"{genre}ランキング"
        ranking=parse_ranking(rank_raw); status.update(label=f"**Step 1｜完了** — {len(ranking)}項目",state="complete")
    except Exception as e:
        status.update(label="Step 1｜エラー",state="error"); st.error(f"エラー: {e}"); st.stop()

with st.status("**Step 2｜クロス集計生成中...**",expanded=True) as status:
    try:
        top3="\n".join([f"{r['rank']}位: {r['label']}（{r['pct']}%）" for r in ranking[:3]])
        cross_raw=ask(client,f"以下のランキングについて{n_size:,}人規模のAIシミュレーションとして\n年代別（20代/30代/40代/50代以上）×性別（男女）の傾向コメントを作成してください。\n\n【ランキングTOP3】\n{top3}\nターゲット：{target}\n\n各項目3〜4行、数値例を含めて。")
        status.update(label="**Step 2｜完了**",state="complete")
    except Exception as e:
        cross_raw=f"（エラー: {e}）"; status.update(label="Step 2｜スキップ",state="error")

with st.status("**Step 3｜ナレーション原稿生成中...**",expanded=True) as status:
    try:
        rank_summary="\n".join([f"{r['rank']}位: {r['label']}（{r['pct']}%）" for r in ranking[:5]])
        script_raw=ask(client,f"以下のAI世論調査ランキングをもとにショート動画（30〜60秒）用コンテンツを作成してください。\n\n【テーマ】{video_title}\n【ターゲット】{target}\n【ランキング】\n{rank_summary}\n\n出力形式：\n【ナレーション原稿】\n（冒頭フック必須。「このデータはAIシミュレーションです」を自然に含める）\n\n【動画タイトル案】\n1. \n2. \n3. ")
        sm=re.search(r'【ナレーション原稿】([\s\S]*?)(?:【動画タイトル案】|$)',script_raw); tm=re.search(r'【動画タイトル案】([\s\S]*)$',script_raw)
        script_text=sm.group(1).strip() if sm else script_raw
        title_ideas=[re.sub(r'^\d+\.\s*','',l).strip() for l in tm.group(1).strip().split("\n") if l.strip()] if tm else []
        status.update(label="**Step 3｜完了**",state="complete")
    except Exception as e:
        script_text=f"（エラー: {e}）"; title_ideas=[]; status.update(label="Step 3｜スキップ",state="error")

with st.status("**Step 4｜グラフPNG生成中...**",expanded=True) as status:
    try:
        graphs=make_all_graphs(ranking,video_title,n_size); status.update(label=f"**Step 4｜完了** — {len(graphs)}枚",state="complete")
    except Exception as e:
        graphs={}; status.update(label=f"Step 4｜エラー: {e}",state="error")

save_to_history({"date":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),"theme_key":theme_key,"title":video_title,"genre":genre,"keyword":keyword,"target":target,"ranking":ranking,"script":script_text,"title_ideas":title_ideas})

st.divider()
st.subheader(f"📌 {video_title}")
tab1,tab2,tab3,tab4,tab5=st.tabs(["🏆 ランキング","📊 クロス集計","🎙️ 原稿","🖼️ グラフ素材","⬇️ 一括DL"])

with tab1:
    max_pct=ranking[0]["pct"] if ranking else 100
    for r in ranking:
        medal={1:"🥇",2:"🥈",3:"🥉"}.get(r["rank"],f"**{r['rank']}位**"); c1,c2,c3=st.columns([0.5,3,1])
        c1.markdown(medal); c2.progress(r["pct"]/max_pct,text=r["label"]); c3.markdown(f"**{r['pct']}%**")

with tab2:
    st.text_area("年代別×性別 クロス集計サマリー",cross_raw,height=300)

with tab3:
    st.text_area("ナレーション原稿",script_text,height=260)
    if title_ideas:
        st.markdown("**動画タイトル案**")
        for t in title_ideas: st.markdown(f"- {t}")

with tab4:
    graph_labels={"graph_01_overall.png":"全体ランキング","graph_02_age.png":"年代別比較","graph_03_gender.png":"性別比較","graph_04_cross.png":"クロス集計","graph_05_vertical.png":"縦型サムネイル"}
    cols=st.columns(2)
    for i,(name,data) in enumerate(graphs.items()):
        with cols[i%2]:
            st.caption(graph_labels.get(name,name)); st.image(data,use_container_width=True)
            st.download_button(label=f"⬇ {graph_labels.get(name,name)}をDL",data=data,file_name=name,mime="image/png",key=name)

with tab5:
    if graphs:
        zip_data=make_zip(graphs); st.success(f"グラフ {len(graphs)}枚をZIPにまとめました")
        st.download_button(label="⬇ グラフ全枚をZIPでダウンロード",data=zip_data,file_name="survey_graphs.zip",mime="application/zip",use_container_width=True)
    else:
        st.warning("グラフの生成に失敗しました")
