import re,io,zipfile,json,os,datetime
import numpy as np
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from anthropic import Anthropic

FONT_PATH="/workspaces/ai-survey-app/NotoSansJP.ttf"
if os.path.exists(FONT_PATH):
    fm.fontManager.addfont(FONT_PATH)
    JP_FONT=fm.FontProperties(fname=FONT_PATH).get_name()
else:
    JP_FONT="DejaVu Sans"
plt.rcParams["font.family"]=JP_FONT
plt.rcParams["axes.unicode_minus"]=False

HISTORY_FILE="/tmp/survey_history.json"
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return []
    return []
def save_to_history(r):
    h=load_history(); h.insert(0,r); h=h[:50]
    with open(HISTORY_FILE,"w",encoding="utf-8") as f: json.dump(h,f,ensure_ascii=False,indent=2)
def get_past_themes(): return [h.get("theme_key","") for h in load_history()]

st.set_page_config(page_title="AI世論調査 全自動生成システム",page_icon="📊",layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.5rem;}
.stButton>button{width:100%;background:#2B4C9B;color:#fff;border:none;border-radius:8px;padding:12px;font-size:15px;font-weight:600;}
.stButton>button:hover{background:#1e3a7a;color:#fff;}
.history-card{background:#f8f9fd;border-radius:8px;padding:10px 14px;margin-bottom:8px;border-left:3px solid #2B4C9B;font-size:13px;}
</style>""",unsafe_allow_html=True)

BG="#0d1020";TC="#ffffff";ST="#aabbdd"
BLUES=["#2B4C9B","#4a7fd4","#7B9FE0","#B5D4F4","#dce9f8","#a0b8e8","#6080c0","#3a5aaa","#8090d0","#c0d0f0"]
GCOL={"M":"#4a7fd4","F":"#e05c8a"}
AGES=["20代","30代","40代","50代以上"]
AGEC=["#2B4C9B","#4a7fd4","#7B9FE0","#B5D4F4"]

def fp(): return fm.FontProperties(fname=FONT_PATH) if os.path.exists(FONT_PATH) else None
def _style():
    plt.rcParams.update({"figure.facecolor":BG,"axes.facecolor":BG,"axes.edgecolor":"#334466","axes.labelcolor":TC,"xtick.color":ST,"ytick.color":TC,"text.color":TC,"grid.color":"#223355","grid.alpha":0.5,"font.family":JP_FONT})
def _note(fig): fig.text(0.98,0.01,"※AIシミュレーション",ha="right",fontsize=8,color="#556688",fontproperties=fp())
def _save(fig):
    buf=io.BytesIO(); fig.savefig(buf,dpi=150,bbox_inches="tight",facecolor=BG); plt.close(fig); return buf.getvalue()

def make_graphs(ranking,title,n):
    _style(); f=fp()
    tn=min(len(ranking),10); lb=[r["label"] for r in ranking[:tn]]; pc=[r["pct"] for r in ranking[:tn]]; cl=BLUES[:tn]; gs={}
    st2=title[:22]+"…" if len(title)>22 else title; cap=f"AIシミュレーション n={n:,}人"

    fig,ax=plt.subplots(figsize=(9,5.5)); y=np.arange(tn)[::-1]
    ax.barh(y,pc,color=cl,height=0.55,zorder=3)
    mc=["#FFD700","#C0C0C0","#CD7F32"]+[ST]*(tn-3)
    for i,(bar,val) in enumerate(zip(ax.patches,pc)):
        ax.text(val+0.8,bar.get_y()+bar.get_height()/2,f"{val}%",va="center",ha="left",fontsize=12,fontweight="bold",fontproperties=f)
        ax.text(-1.2,bar.get_y()+bar.get_height()/2,f"{ranking[i]['rank']}位",va="center",ha="right",fontsize=10,color=mc[i],fontproperties=f)
    ax.set_yticks(y); ax.set_yticklabels(lb[::-1],fontsize=11,fontproperties=f)
    ax.set_xlim(-6,max(pc)+14); ax.grid(axis="x",zorder=0); ax.spines[:].set_visible(False)
    ax.set_title(f"{st2}\n({cap})",fontsize=13,fontweight="bold",pad=14,fontproperties=f); _note(fig); plt.tight_layout()
    gs["graph_01_overall.png"]=_save(fig)

    t5=lb[:5]; t5p=pc[:5]; rng=np.random.default_rng(42)
    ad={a:[max(0,min(100,v+rng.integers(-12,13))) for v in t5p] for a in AGES}
    fig,ax=plt.subplots(figsize=(10,5.5)); x=np.arange(len(t5)); w=0.18
    for i,(age,vals) in enumerate(ad.items()):
        offs=(-1.5+i)*w; bs=ax.bar(x+offs,vals,w*0.9,label=age,color=AGEC[i],zorder=3)
        for b,v in zip(bs,vals): ax.text(b.get_x()+b.get_width()/2,b.get_height()+0.6,str(v),ha="center",fontsize=8,fontproperties=f)
    ax.set_xticks(x); ax.set_xticklabels(t5,fontsize=10,fontproperties=f)
    ax.set_ylim(0,95); ax.grid(axis="y",zorder=0); ax.spines[:].set_visible(False)
    ax.legend(fontsize=10,framealpha=0.15,facecolor="#1a2a4a",labelcolor=TC,prop=f)
    ax.set_title(f"年代別｜{st2}\n({cap})",fontsize=12,fontweight="bold",pad=14,fontproperties=f); _note(fig); plt.tight_layout()
    gs["graph_02_age.png"]=_save(fig)

    rng2=np.random.default_rng(7); mv=[max(0,min(100,v+rng2.integers(-10,8))) for v in t5p]; fv=[max(0,min(100,v+rng2.integers(-8,12))) for v in t5p]
    fig,ax=plt.subplots(figsize=(9,5.5)); yy=np.arange(len(t5)); ww=0.36
    ax.barh(yy+ww/2,mv,ww*0.9,label="男性",color=GCOL["M"],zorder=3); ax.barh(yy-ww/2,fv,ww*0.9,label="女性",color=GCOL["F"],zorder=3)
    for i,(m,fval) in enumerate(zip(mv,fv)):
        ax.text(m+0.6,yy[i]+ww/2,f"{m}%",va="center",fontsize=10,fontproperties=f)
        ax.text(fval+0.6,yy[i]-ww/2,f"{fval}%",va="center",fontsize=10,fontproperties=f)
    ax.set_yticks(yy); ax.set_yticklabels(t5,fontsize=11,fontproperties=f)
    ax.set_xlim(0,max(mv+fv)+16); ax.grid(axis="x",zorder=0); ax.spines[:].set_visible(False)
    ax.legend(fontsize=11,framealpha=0.15,facecolor="#1a2a4a",labelcolor=TC,prop=f)
    ax.set_title(f"性別比較｜{st2}\n({cap})",fontsize=12,fontweight="bold",pad=14,fontproperties=f); _note(fig); plt.tight_layout()
    gs["graph_03_gender.png"]=_save(fig)

    base=pc[0]; rng3=np.random.default_rng(13)
    mc2=[max(0,min(100,base+rng3.integers(-15,5))) for _ in AGES]; fc2=[max(0,min(100,base+rng3.integers(-5,15))) for _ in AGES]
    fig,ax=plt.subplots(figsize=(9,4.5)); xx=np.arange(len(AGES)); wc=0.35
    bm=ax.bar(xx-wc/2,mc2,wc*0.9,label="男性",color=GCOL["M"],zorder=3); bf=ax.bar(xx+wc/2,fc2,wc*0.9,label="女性",color=GCOL["F"],zorder=3)
    for b,v in zip(bm,mc2): ax.text(b.get_x()+b.get_width()/2,b.get_height()+0.8,f"{v}%",ha="center",fontsize=11,fontweight="bold",fontproperties=f)
    for b,v in zip(bf,fc2): ax.text(b.get_x()+b.get_width()/2,b.get_height()+0.8,f"{v}%",ha="center",fontsize=11,fontweight="bold",fontproperties=f)
    ax.set_xticks(xx); ax.set_xticklabels(AGES,fontsize=12,fontproperties=f)
    ax.set_ylim(0,max(mc2+fc2)+16); ax.grid(axis="y",zorder=0); ax.spines[:].set_visible(False)
    ax.legend(fontsize=11,framealpha=0.15,facecolor="#1a2a4a",labelcolor=TC,prop=f)
    ax.set_title(f"クロス集計｜1位「{lb[0]}」\n({cap})",fontsize=12,fontweight="bold",pad=14,fontproperties=f); _note(fig); plt.tight_layout()
    gs["graph_04_cross.png"]=_save(fig)

    fig2=plt.figure(figsize=(5,9)); fig2.patch.set_facecolor(BG); ax2=fig2.add_axes([0.18,0.08,0.76,0.68]); ax2.set_facecolor(BG)
    yv=np.arange(min(5,tn))[::-1]
    for i,(yi,val,col) in enumerate(zip(yv,pc[:5],cl[:5])):
        ax2.barh(yi,val,color=col,height=0.58,zorder=3)
        ax2.text(val+0.8,yi,f"{val}%",va="center",fontsize=13,fontweight="bold",fontproperties=f)
        ax2.text(-0.5,yi,lb[i],va="center",ha="right",fontsize=9,fontproperties=f)
    ax2.set_xlim(-20,max(pc[:5])+18); ax2.set_yticks([]); ax2.grid(axis="x",zorder=0,alpha=0.3); ax2.spines[:].set_visible(False)
    fig2.text(0.5,0.91,st2,ha="center",fontsize=16,fontweight="bold",fontproperties=f)
    fig2.text(0.5,0.96,cap,ha="center",fontsize=10,color="#7B9FE0",fontproperties=f)
    fig2.text(0.5,0.02,"※AIシミュレーション",ha="center",fontsize=8,color="#556688",fontproperties=f)
    gs["graph_05_vertical.png"]=_save(fig2)
    return gs

def make_zip(gs):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w") as zf:
        for n,d in gs.items(): zf.writestr(n,d)
    return buf.getvalue()

def ask(client,prompt):
    msg=client.messages.create(model="claude-opus-4-6",max_tokens=2000,messages=[{"role":"user","content":prompt}])
    return msg.content[0].text

def parse_ranking(text):
    items=[]
    for line in text.split("\n"):
        m=re.match(r'(\d+)位[：:]\s*(.+?)\s*[\/／]\s*支持率\s*(\d+)%',line)
        if m: items.append({"rank":int(m[1]),"label":m[2].strip(),"pct":int(m[3])})
    return items

VIDEO_FORMATS={
    "ショート（15秒）":{"sec":15,"desc":"15秒・インパクト重視","hook":"3秒以内の超強烈フック","body":"1位の結果のみ紹介","cta":"フォロー誘導1文","words":"約60文字"},
    "ショート（30秒）":{"sec":30,"desc":"30秒・TikTok/Reels向け","hook":"5秒以内のフック","body":"TOP3を簡潔に紹介","cta":"共感・保存誘導","words":"約120文字"},
    "ショート（60秒）":{"sec":60,"desc":"60秒・YouTube Shorts向け","hook":"冒頭フック→結果予告","body":"TOP5を順番に紹介","cta":"コメント・フォロー誘導","words":"約240文字"},
    "通常（3分）":{"sec":180,"desc":"3分・YouTube向け","hook":"冒頭30秒で興味喚起","body":"全順位＋年代別傾向も紹介","cta":"チャンネル登録・コメント誘導","words":"約720文字"},
    "通常（5分）":{"sec":300,"desc":"5分・詳細解説向け","hook":"冒頭で問題提起＋予告","body":"全順位＋クロス集計＋考察","cta":"チャンネル登録・概要欄誘導","words":"約1200文字"},
    "通常（10分）":{"sec":600,"desc":"10分・深掘り解説向け","hook":"冒頭1分で世界観構築","body":"全順位＋詳細分析＋視聴者への問いかけ","cta":"チャンネル登録・コミュニティ誘導","words":"約2400文字"},
}

with st.sidebar:
    st.markdown("## ⚙️ テーマ設定")
    api_key=st.text_input("Anthropic APIキー",type="password",placeholder="sk-ant-...")
    genre=st.selectbox("ジャンル",["ライフスタイル","お金・副業","恋愛・人間関係","仕事・キャリア","エンタメ・雑学"])
    keyword=st.text_input("キーワード",placeholder="例：節約、転職、推し活")
    target=st.selectbox("ターゲット視聴者",["20代全般","30代会社員","子育て世代","フリーランス・副業志望","シニア層"],index=2)
    top_n=st.radio("ランキング形式",["TOP5","TOP10"],horizontal=True)
    top_n_int=int(top_n.replace("TOP",""))
    n_size=st.select_slider("サンプル規模",options=[1000,3000,5000,10000],value=10000,format_func=lambda x:f"{x:,}人")
    st.markdown("---")
    video_fmt=st.selectbox("🎬 動画の長さ・形式",list(VIDEO_FORMATS.keys()),index=2)
    vf=VIDEO_FORMATS[video_fmt]
    st.caption(f"📝 原稿の目安：{vf['words']} ／ {vf['desc']}")
    theme_key=f"{genre}_{keyword}_{target}"
    if theme_key in get_past_themes(): st.warning("⚠️ このテーマは過去に生成済みです。")
    run=st.button("▶ 全自動生成スタート",use_container_width=True)
    st.divider()
    st.markdown("### 📂 生成履歴")
    history=load_history()
    if not history: st.caption("まだ履歴がありません")
    else:
        for h in history[:5]:
            st.markdown(f"<div class='history-card'><b>{h.get('title','')}</b><br><span style='color:#888;font-size:11px;'>{h.get('date','')} ／ {h.get('genre','')} ／ {h.get('video_fmt','')}</span></div>",unsafe_allow_html=True)

st.title("📊 AI世論調査 全自動生成システム")
st.caption("テーマ入力 → ランキング生成 → クロス集計 → グラフPNG → 原稿　をワンクリックで一括出力")

if not run:
    st.info("左のサイドバーでテーマと動画の長さを設定して「全自動生成スタート」を押してください。")
    if history:
        st.subheader("最近の生成")
        cols=st.columns(min(3,len(history)))
        for i,h in enumerate(history[:3]):
            with cols[i]: st.markdown(f"**{h.get('title','')}**"); st.caption(f"{h.get('date','')} ／ {h.get('video_fmt','')}")
    st.stop()

if not api_key: st.error("APIキーを入力してください"); st.stop()
client=Anthropic(api_key=api_key)

with st.status("**Step 1｜ランキング生成中...**",expanded=True) as status:
    try:
        rank_raw=ask(client,f"ジャンル「{genre}」、キーワード「{keyword or 'なし'}」、ターゲット「{target}」のTOP{top_n_int}ランキングを作成してください。\nWeb上のトレンド・統計を参考にしたAIシミュレーションとして出力してください。\n\n必ずこの形式で：\n【タイトル】キャッチーな動画タイトル一文\n【ランキング】\n"+"\n".join([f"{i+1}位: 項目名 / 支持率XX%" for i in range(top_n_int)])+"\n【コメント】各順位に共感できる一言")
        title_m=re.search(r'【タイトル】\s*(.+)',rank_raw); video_title=title_m.group(1).strip() if title_m else f"{genre}ランキング"
        ranking=parse_ranking(rank_raw); status.update(label=f"**Step 1｜完了** — {len(ranking)}項目",state="complete")
    except Exception as e: status.update(label="Step 1｜エラー",state="error"); st.error(f"エラー: {e}"); st.stop()

with st.status("**Step 2｜クロス集計生成中...**",expanded=True) as status:
    try:
        top3="\n".join([f"{r['rank']}位: {r['label']}（{r['pct']}%）" for r in ranking[:3]])
        cross_raw=ask(client,f"以下のランキングについて{n_size:,}人規模のAIシミュレーションとして年代別（20代/30代/40代/50代以上）×性別（男女）の傾向コメントを作成してください。\n\n【ランキングTOP3】\n{top3}\nターゲット：{target}\n\n各項目3〜4行、数値例を含めて。")
        status.update(label="**Step 2｜完了**",state="complete")
    except Exception as e: cross_raw=f"（エラー: {e}）"; status.update(label="Step 2｜スキップ",state="error")

with st.status(f"**Step 3｜ナレーション原稿生成中（{video_fmt}）...**",expanded=True) as status:
    try:
        rank_summary="\n".join([f"{r['rank']}位: {r['label']}（{r['pct']}%）" for r in ranking[:top_n_int]])
        script_prompt=f"""以下のAI世論調査ランキングをもとに、{video_fmt}（{vf['sec']}秒）用のナレーション原稿を作成してください。

【テーマ】{video_title}
【ターゲット】{target}
【ランキング】
{rank_summary}

【原稿の要件】
- 動画の長さ：{video_fmt}（{vf['sec']}秒）
- 目安文字数：{vf['words']}
- 冒頭：{vf['hook']}
- 本編：{vf['body']}
- 締め：{vf['cta']}
- 「このデータはAIシミュレーションです」を自然に含める
- テンポよく読めるよう句読点を適切に使う

出力形式：
【ナレーション原稿】
（原稿本文）

【動画タイトル案】
1. 
2. 
3. 

【テロップ案】
各ランキング項目に添える短いコピーを1行ずつ"""

        script_raw=ask(client,script_prompt)
        sm=re.search(r'【ナレーション原稿】([\s\S]*?)(?:【動画タイトル案】|$)',script_raw)
        tm=re.search(r'【動画タイトル案】([\s\S]*?)(?:【テロップ案】|$)',script_raw)
        telop_m=re.search(r'【テロップ案】([\s\S]*)$',script_raw)
        script_text=sm.group(1).strip() if sm else script_raw
        title_ideas=[re.sub(r'^\d+\.\s*','',l).strip() for l in tm.group(1).strip().split("\n") if l.strip()] if tm else []
        telop_text=telop_m.group(1).strip() if telop_m else ""
        status.update(label=f"**Step 3｜完了** — {video_fmt}用原稿生成済み",state="complete")
    except Exception as e: script_text=f"（エラー: {e}）"; title_ideas=[]; telop_text=""; status.update(label="Step 3｜スキップ",state="error")

with st.status("**Step 4｜グラフPNG生成中...**",expanded=True) as status:
    try:
        graphs=make_graphs(ranking,video_title,n_size); status.update(label=f"**Step 4｜完了** — {len(graphs)}枚",state="complete")
    except Exception as e: graphs={}; status.update(label=f"Step 4｜エラー: {e}",state="error")

save_to_history({"date":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),"theme_key":theme_key,"title":video_title,"genre":genre,"keyword":keyword,"target":target,"video_fmt":video_fmt,"ranking":ranking,"script":script_text,"title_ideas":title_ideas})

st.divider()
st.subheader(f"📌 {video_title}")
st.caption(f"🎬 {video_fmt} ／ 目安：{vf['words']}")
tab1,tab2,tab3,tab4,tab5=st.tabs(["🏆 ランキング","📊 クロス集計","🎙️ 原稿・テロップ","🖼️ グラフ素材","⬇️ 一括DL"])

with tab1:
    max_pct=ranking[0]["pct"] if ranking else 100
    for r in ranking:
        medal={1:"🥇",2:"🥈",3:"🥉"}.get(r["rank"],f"**{r['rank']}位**"); c1,c2,c3=st.columns([0.5,3,1])
        c1.markdown(medal); c2.progress(r["pct"]/max_pct,text=r["label"]); c3.markdown(f"**{r['pct']}%**")

with tab2:
    st.text_area("年代別×性別 クロス集計サマリー",cross_raw,height=300)

with tab3:
    col1,col2=st.columns([3,1])
    with col1:
        st.markdown(f"**🎬 {video_fmt}用ナレーション原稿**（目安：{vf['words']}）")
        st.text_area("原稿",script_text,height=320,label_visibility="collapsed")
    with col2:
        st.markdown("**動画タイトル案**")
        for t in title_ideas: st.markdown(f"- {t}")
    if telop_text:
        st.markdown("**テロップ案**")
        st.text_area("テロップ",telop_text,height=180,label_visibility="collapsed")

with tab4:
    gl={"graph_01_overall.png":"全体ランキング","graph_02_age.png":"年代別比較","graph_03_gender.png":"性別比較","graph_04_cross.png":"クロス集計","graph_05_vertical.png":"縦型サムネイル"}
    cols=st.columns(2)
    for i,(name,data) in enumerate(graphs.items()):
        with cols[i%2]:
            st.caption(gl.get(name,name)); st.image(data,use_container_width=True)
            st.download_button(label=f"⬇ {gl.get(name,name)}をDL",data=data,file_name=name,mime="image/png",key=name)

with tab5:
    if graphs:
        zd=make_zip(graphs); st.success(f"グラフ {len(graphs)}枚をZIPにまとめました")
        st.download_button(label="⬇ グラフ全枚をZIPでダウンロード",data=zd,file_name="survey_graphs.zip",mime="application/zip",use_container_width=True)
    else: st.warning("グラフの生成に失敗しました")
