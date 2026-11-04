# Blender 底片层（Blender plates）设计

日期：2026-11-04 · 状态：待用户批准（§9 的问题已答） · 分支：`blender-plates`

## 1. 为什么做，做成什么样

用户的判断：Blender 在 3D 物品和场景上有明显优势，应该"基于一些规则来突出 Blender 的长处，并与 Remotion 较好融合"。

实验（`~/code_project/film_work/blender_spike`，桌面 `Blender实验/`）证明了三件事：

1. **融合通道是通的。** Blender 渲出 3D 底片并逐帧导出关键点；一个 Remotion 镜头把底片当背景播放，在这些点上叠加信号帧、标注和标题。镜头推近时，叠加物一直贴着天线阵。
2. **真实世界的素材一用就赢。** NASA 的 24k 地球贴图加上大气边缘光，明显好过 2.5D 的弧线。
3. **靠脚本"盲搭"的设计物体赢不了。** 程序化建模的卫星只和原版 2.5D 卫星打平。调了 6 张静帧才能看，前 4 张的问题都是可以预防的。

所以本设计**不是**"用 Blender 做视频"，而是给 remotion 层加第三种镜头来源，叫 **Blender 底片**。它只出现在"3D 的物理性本身就是内容"的拍上。文字、字幕、时序、数据、界面、版式仍然全部归 Remotion。

## 2. 目标 / 非目标 / 反目标

**目标**
- 一套**路由规则**，判断哪一拍值得用 Blender，并把理由写进 `shot_fit`。
- 一份**底片契约**，规定 Blender 交给 Remotion 的东西：透明底片、锚点、物体遮罩、相机数据。现有的版式、字幕、同步检查因此能"看见" 3D 物体。
- 一套 **Blender kit**，包含构图、灯光、材质、资产获取四部分，把实验里那 4 轮试错变成默认值。
- 一个**看图回路**：先出静帧样张，看过之后才渲全片；能测量的问题做成闸门。
- 成本**可预估、可缓存**：渲染前给出时间预算，没变的底片不重渲。

**非目标（v1 不做）**
- 整部片用 Blender，或用 Blender 排正文和字幕。
- AI 生成 3D 模型（如 Hyper3D Rodin）：要付费，授权和质量都不确定。
- 云渲染农场（付费）。
- 手工编辑的 `.blend` 文件：所有场景都由脚本生成，可复现。
- HTML 层接入（见 §9 待定问题）。

**反目标（技术上能跑，但算失败）**
- 底片成了装饰：Blender 画的东西把字幕盖住后不再表达这一拍的意思（违反 design-must-be-meaningful）。
- 盲搭的 3D 物体比现有 2.5D 镜头更粗糙，却因为"是 3D"被选上。
- 底片纯黑或自带一套颜色，和全片底色、DNA 配色脱节。
- 一部片的渲染时间失控，或者改一句旁白就要重渲所有 3D。

## 3. 路由规则：什么时候用 Blender

这一拍的理想画面（`shot_fit.ideal`，先写理想画面，再定路线）至少要满足下面一类，才可以走 `route: "blender"`。理由类别写进 `shot_fit.blender_why`，取值是一个封闭的词表：

| 类别 `blender_why` | 例子 | 为什么 Remotion 做不好 |
|---|---|---|
| `real-world` 真实的物或地方，有真实数据或扫描 | 地球、行星（NASA 影像）；地形（高程数据）；博物馆扫描件（Smithsonian CC0）；分子（PDB 结构） | 2.5D 只能画示意，真实贴图和扫描才可信 |
| `material` 物理材质就是看点 | 金属、玻璃、液体、半透明、次表面散射；产品主视觉（形状已知、有参考） | CSS 和 SVG 没有真实的反射与折射 |
| `physics` 物理过程就是内容 | 刚体碰撞、布料、流体、烟雾、粒子（烘焙模拟） | Remotion 只能手写近似的运动 |
| `optics` 光学现象 | 焦散、折射、体积光、微距景深 | 需要路径追踪 |
| `space` 空间与尺度 | 穿行一个 3D 结构；机器内部；带真实部件的爆炸图 | 2.5D 的视差撑不住大幅度相机运动 |

**禁止走 Blender 的情况**：正文或版式即画面、图表与数据（用现有的数据镜头）、界面、示意图、抽象概念、任何靠文字表达意思的拍。

**选择规则**
- **先比再选。** 同一拍，如果库里已有能表达它的 2.5D 镜头，先各出一张静帧并排比较，Blender 版要明显更好才用。这和现有的"构图竞争"做法一致。
- **设计物体必须有参考。** Blender 里建的物体要像现有物体一样填 fidelity 记录（零部件、比例、来源参考）。找不到可信模型或参考的，不走 Blender。
- **预算。** 默认一部片里 Blender 拍不超过 30%，底片总长不超过约 40 秒。超过就提示用户，由用户决定。

## 4. 底片契约：Blender 交给 Remotion 什么

每个 Blender 拍输出到 `media/blender/<beat_id>/`：

| 文件 | 内容 | 用途 |
|---|---|---|
| `rgba/%04d.png` | 透明背景（`film_transparent`，RGBA）的底片序列 | Remotion 把它叠在全片自己的底色上（`bgGrad`），解决实验里"纯黑背景"的问题 |
| `env/%04d.png`（可选） | 不透明的环境底片 | 当世界本身就是内容时用（太空、地形）。每拍二选一，并在契约里写明 |
| `anchors.json` | 逐帧具名 3D 点的屏幕坐标，附带深度和是否被遮挡 | 叠加物贴在 3D 物体上（实验里的 `antenna`、`limb`） |
| `ids/%04d.png` + `boxes.json` | 每个具名物体一种纯色的 ID 图，以及由它算出的逐帧包围框 | 版面检查（text_safe、字幕带、叠加物与物体相撞）把 3D 物体当作内容框 |
| `camera.json` | 逐帧相机内参和外参 | 需要时让 Remotion 的 three.js 层或 DOM 元素做 3D 跟随 |
| `plate.json` | 引擎、采样、分辨率、Blender 版本、资产清单与授权、用到的提示词时间、缓存键 | 审计与缓存 |

**实测**
- EEVEE 5.2 的渲染层不输出 Object Index 通道（只有 Image/Alpha），所以 ID 图用 **Workbench 平涂单独渲一遍**：在 960×540 下每帧 0.72 秒，遮挡关系正确，颜色干净，只有亚像素级的近似色，按最近的主色归类即可。
- 透明 RGBA 输出可用。

**时间**
- 底片按这一拍自己的秒数来写，事件时间取自 `words.json`，和实验里"广播"一词的做法一样。
- 规则：随词出现的东西优先放在 Remotion 叠加层，底片里只放连续的环境运动。确实需要 3D 事件落在某个词上的（比如一个物体在词上碎开），可以写进底片，但那个词的时间会进入缓存键。

**缓存**
- 底片的缓存键 = 场景脚本 + kit 版本 + 资产 sha256 + 用到的提示词时间 + Blender 版本 + 分辨率和引擎。
- 底片重建后，这一拍走现有的分段缓存规则重渲。

**Remotion 侧**
- 新增一个运行时组件 `BlenderPlate`。它负责播放底片、按帧提供锚点和包围框，并把包围框登记给版面检查。
- 拍自己的镜头（工坊镜头）只管画叠加内容，就像实验里的 `BroadcastPlate`。

## 5. Blender kit：把试错变成默认值

位置：`blender/kit/*.py`。只靠 bpy 和标准库，由 `blender -b --factory-startup --python` 调用。

- **`stage.py` 构图**：在**相机空间**里放物体，按视角和屏幕占比定位置和大小，并能把某个特征面转向镜头（实验里有效的做法）。另外提供"主体应占画面多少"的断言。
- **`lightrig.py` 灯光**：预设 `studio`（主光、补光、轮廓光，加反射穹顶）、`space`（太阳、地球反照光、反射穹顶）、`dark-premium`、`high-key`。
  - 颜色从影片 DNA 推出，比如轮廓光取 accent 色。
  - 反射穹顶用 Light Path 的 Is Camera Ray 节点做：镜头看到的是背景，反射时看到的是影棚环境。这是实验里修好"金属发黑"的方法。
- **`materials.py` 材质库**：拉丝金属、阳极氧化铝、玻璃、塑料、陶瓷、MLI 金箔、太阳能电池片等。每种材质调好一次，用材质样张固定下来。
- **`assets.py` 资产**：拉取资产并在旁边写授权说明（sidecar），和现有 imagefetch 的规则一样。来源：
  - Poly Haven：全部 CC0，有 HDRI、贴图、模型，`api.polyhaven.com`，使用前先读它的 API 条款；
  - NASA 3D Resources：GLB 格式，官方说明是"free and without copyright"，但每个模型要再核对使用指南；
  - Smithsonian 3D：用 CC0 筛选，GLB 格式；
  - NASA 影像：地球等。

  每次下载先问用户（全局规则）。validate 拒绝任何没有授权说明的底片资产。
- **`anchors.py`、`idpass.py`、`render.py`**：
  - 只用 GPU。实测 CPU 和 GPU 同开时，128 采样每帧 67 秒，只开 GPU、64 采样每帧 13–19 秒。
  - 输出 PNG 序列，可断点续渲，最后用 ffmpeg 编码。
  - `--preview` 用 50% 分辨率和低采样。
- **版本**：Blender 不低于 5.0。5.0 把 EEVEE 的引擎名改成了 `BLENDER_EEVEE`，并移除了 `scene.node_tree`，改用 `compositing_node_group`。
  - 这台机器上是 5.2.4 LTS 的候选版（RC），doctor.py 要检查路径和版本，遇到 RC 给出警告。
  - Blender 不在 PATH 上，路径用 `meta.blender` 或环境变量指定。

## 6. 看图回路与闸门

研究依据：SceneCraft（ICML 2024）让大模型写 Blender 代码，每轮渲染后用视觉模型点评再改。它的消融实验显示，去掉这个视觉反馈内循环，约束得分下降 38.4 分。实验里我前 4 张静帧的错误，也都要靠看图才能发现。所以看图是必选步骤，不是可选项。

- **`blender_proof.py`**：对每个 Blender 拍，以 50% 分辨率出首帧、中段、落定帧（约 90%）三张，拼成对比小样。导演先看过，才允许渲全片。
- **`plate_qa.py`**（阻断性闸门），只查能测量的：
  - 主体覆盖：用 ID 图测主体的位置和占比，和 `stage.py` 声明的意图比较（会抓到"地球在画面外"这类问题）；
  - 主体亮度：主体像素里接近纯黑的比例（会抓到"金属反射黑空间"）；
  - 贴图放大倍数：沿用 media_res_qa 的思路，贴图的纹素密度不能低于屏幕像素；
  - 时间噪声：逐帧之间静止区域的闪烁（EEVEE 的 TAA 噪声）；
  - 叠加物与物体相撞：Remotion 叠加的文字框与 `boxes.json` 求交（会抓到"机翼压住'我在哪'"）。
- **样张对比**：§3 的"先比再选"由这一步出图，用户或评审依据看图判断。

## 7. 3D 文字

实测：Blender 5.2 的文字对象指定中文字体（这次是 STHeiti）后，中文立体字能正常渲染，但**不会自动换行**。

规则：Blender 里只允许放很短的立体标题词（例如不超过 8 个字），而且要求 3D 材质本身就是看点。字体取影片 DNA 的字体文件，保证全片一致。其余所有文字都归 Remotion。

## 8. 成本模型（实测，Apple M4 10 核 GPU，24 GB）

| 引擎与内容 | 每帧 |
|---|---|
| EEVEE，简单场景，1080p | 3.4 秒 |
| EEVEE，实验底片（卫星 + 24k 地球），1080p | 4.6 秒（169 帧 783 秒） |
| Cycles，只用 GPU，64 采样 + 降噪，简单场景 | 13–19 秒 |
| Workbench ID 图，960×540 | 0.72 秒 |
| Remotion 合成这一拍 | 47 秒（原版 31 秒） |

- 例：4 个底片，每个 6 秒，30 fps，共 720 帧。EEVEE 约 55 分钟；换成 Cycles 约 2.6–3.8 小时。
- 渲染前打印预估。超过 `meta.blender_budget_min`（默认值见 §9）时，先问用户。
- 底片渲染放在后台跑，不阻塞其他步骤。

## 9. 用户的决定（2026-11-04）

1. **渲染预算**：`meta.blender_budget_min` 默认 60 分钟。预估超出时先问用户。
2. **范围**：v1 只做 Remotion 层，HTML 层以后再说。
3. **验证题目**：一个真实世界主题，一个产品或材质主题（P4）。
4. **资产下载**：每部片开工时一次性列出全部要下载的资产，写明文件名、来源、大小和授权，问用户一次；之后再加新资产，单独再问。

## 10. 分阶段

- **P0（已完成）**：实验。证明融合通道可用，测出成本和失败模式。
- **P1 契约与核心**：
  - `blender/kit` 的 stage、render、anchors、idpass；
  - 底片目录契约、缓存键、`BlenderPlate` 运行时组件；
  - doctor 检查；
  - 用新契约重做 GPS 片的第 3 拍和第 12 拍。
  - 验收：叠加物贴得住；版面检查能看到 3D 物体；改一句旁白只重渲受影响的底片。
- **P2 质感**：lightrig、materials 和样张，assets 加授权说明，blender_proof，plate_qa。
  - 验收：同一个场景零试错、第一张静帧就能看；第 3 拍的 Blender 版在对比里明显胜过原版，由用户判断。
- **P3 物理与 Cycles**：刚体、布料、流体的烘焙拍，玻璃和焦散走 Cycles 路线，加上预算提示。
- **P4 路由与泛化**：
  - 路由规则写进 shot-director、design-director、validate 和文档；
  - 用 skill 本身、不靠我手把手，做两个新题目来检验泛化（一个真实世界、一个产品或材质）。

每个阶段都先写失败的测试；推送前跑全套测试；每阶段结束时把真实产物给用户看。

## 11. 资料来源

- SceneCraft：https://arxiv.org/abs/2403.01248
- Blender 5.0 EEVEE 变更：https://developer.blender.org/docs/release_notes/5.0/eevee/ ；API 变更：https://docs.blender.org/api/5.0/change_log.html
- 渲染通道、Cryptomatte、Object Index：https://docs.blender.org/manual/en/latest/render/layers/passes.html
- Poly Haven 授权（CC0）：https://www.polyhaven.com/license
- NASA 3D Resources：https://github.com/nasa/NASA-3D-Resources
- Smithsonian 3D Open Access：https://3d.si.edu/collections/openaccesshighlights
- 无头渲染输出图像序列、再用 FFmpeg 编码的做法：https://www.technetexperts.com/blender-python-ffmpeg-error/
- Blender MCP（参考做法：通过 socket 驱动 Blender，接入 Poly Haven）：https://lobehub.com/en/mcp/ahujasid-blender-mcp
