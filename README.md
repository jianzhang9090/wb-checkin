# WorkBuddy 签到值守 · GitHub Actions 部署包（一天一轮）

目标：**电脑关机也照常执行**——每天 09:00（北京时间）签到领 100 积分 + 派猫猫去旅行（一天仅一次）；旅行期间每 10 分钟巡检，猫猫一到达立即领取礼物；领取成功后当天收工，第二天 09:00 自动继续。

原理：脚本走「长效令牌」通道，不依赖电脑、不依赖 WorkBuddy 客户端；GitHub 的机器负责按 cron 执行。

## 一天的行为（严格一轮）

| 时间（北京时间） | 动作 |
|---|---|
| 每天 09:00 | 签到领 100 积分（已签自动跳过）+ 派猫猫旅行（一天仅派遣一次） |
| 09:00–17:00 每 10 分钟 | 旅行巡检：只读状态；**已到达才领取积分，绝不派遣** |
| 领取成功 | 当天任务完成，不再做任何写操作 |
| 第二天 09:00 | 自动开始新的一轮 |

## 部署步骤（约 10 分钟）

1. **建仓库**：GitHub 右上角 `+` → New repository → 名字随意（如 `wb-checkin`）→ 选 **Private** → Create。
2. **上传文件**：在仓库页点 `Add file` → `Upload files`，把本文件夹里的 **全部内容**拖进去（`.github` 文件夹也要一起传；Windows 需先在资源管理器「查看」里勾选「显示隐藏的项目」才能看到它）→ Commit。
   - 或者用 Git Bash（在本文件夹内执行）：
     ```
     git init && git add . && git commit -m "wb checkin" && git branch -M main
     git remote add origin https://github.com/<你的用户名>/<仓库名>.git
     git push -u origin main
     ```
3. **加 Secret**：仓库页 → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`：
   - Name 填 `WB_RT`
   - Value 填 **`C:\Users\jianz\.workbuddy\checkin-rt-gha.json` 文件的全部内容**（用记事本打开全选复制，是一段 JSON）
   - Add secret
4. **测试**：仓库页 → `Actions` → 左侧选 `WorkBuddy 签到值守（一天一轮）` → 右侧 `Run workflow` → 跑完后点进运行记录看日志。输出 `state=traveling` 或 `state=idle` 都算成功（此时应该显示"空闲，今日派遣次数已用完"或类似）。

## 之后会自动运行

- 每天 09:00 前后几分钟：签到 + 派猫（GitHub 定时偶尔延迟几分钟，正常现象）
- 白天每 10 分钟巡检一次，到达即领
- 在 `Actions` 标签页可看每次运行日志

## 注意事项

- **令牌轮换**：每次运行会自动轮换长效令牌并存入 Actions 缓存，无需操心。缓存 7 天不被访问才会清除，而本任务每天多次运行，不会触发。
- **令牌失效时**（日志出现 `令牌刷新失败`）：在电脑上跑 `python "%USERPROFILE%\.workbuddy\scripts\rt_auth.py" --export-rt --save`，把新生成的 `~/.workbuddy/checkin-rt.json` 内容更新到 Secret 即可。
- **单一运行端**：长效令牌同一时间只应有一个执行端。启用本方案后，暂停电脑上的其他执行端（Windows 计划任务 / WorkBuddy 自动化 / 云端沙箱应用），否则会互相顶掉令牌。
- 本仓库是私有的，Secret 只有你能看到；脚本不含任何账号密码，只有调用接口的逻辑。
