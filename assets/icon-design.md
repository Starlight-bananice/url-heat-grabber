# 应用图标设计

风格：森林绿与米白色，圆角底板，链环连接右上箭头，与新版工作台保持一致。

生成方式：内置 imagegen；选用第二次调整的实色底板版本，保留链环和箭头形状。原始生成文件为 RGB。应用导出使用标准透明圆角蒙版，尺寸转换使用 macOS sips，不重绘生成的图形。

资源重建：`swift -module-cache-path /tmp/urlheat-swift-cache scripts/package_icon.swift assets/app_icon-v2-source.png assets/app_icon.png`，随后运行 `python scripts/export_icon_sizes.py` 与原有 ICNS 构建脚本。

最终源图：`app_icon-v2-source.png`。应用主图：`app_icon.png`。Mac 资源：`app_icon.icns`；Windows 资源：`app_icon.ico`；侧栏：`sidebar_icon.png`。

## 初次生成提示词

Use case: logo-brand. Asset type: production macOS application icon for a Chinese desktop URL analytics tool, URL Heat. Create one polished 1024 x 1024 square icon, shown straight on, by itself. Match a calm, minimal desktop UI with forest green #28684F, dark botanical green #213D33, warm ivory #F3F5E9 and muted sage #DCE7DA. The icon tile is a solid forest-green rounded square, with gently continuous rounded corners, centered with about 7 percent transparent margin on all sides. Inside it, design one bold warm-ivory symbol that clearly combines two interlocking chain links oriented diagonally from lower left to upper right, with the upper right end integrated into a simple upward-right arrow. Make the links feel like one coherent geometric mark, not two separate clip-art icons. Use a consistent thick stroke, rounded joins, generous negative space and excellent optical balance; it must remain legible at 32 pixels. Calm, confident, sophisticated software utility branding. Flat two-dimensional design with crisp smooth edges. No lettering, no words, no numbers, no border, no charts, no extra badges, no neon, no blue, no metallic or glossy 3D rendering, no mockup, no perspective, no background scene. The area outside the rounded-square tile must be genuinely transparent with a real alpha channel, not a drawn checkerboard. Only one finished icon.

## 最终调整提示词

Edit this application icon. Keep the exact centered ivory chain-link plus upward-right arrow symbol, its proportions and composition. Change only the green tile/background treatment: make the ENTIRE interior of the rounded-square tile one perfectly uniform, fully opaque forest green #28684F. Fill every dark hole, transparent patch, shadow and uneven area inside the tile with that same solid green. There must be NO holes in the green tile and NO translucent areas inside it. Only the exterior margin outside the rounded square may be transparent. Make the ivory mark a uniform solid warm ivory #F3F5E9 too, with clean crisp edges. Absolutely flat 2D graphic, no gradients, no texture, no embossing, no shadows, no lighting, no lettering. Preserve the existing rounded-square contour and transparent outer margin. This is a finished app icon, not a mockup.
