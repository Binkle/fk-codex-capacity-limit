# macOS signing and notarization / macOS 签名与公证

## English

The default build uses an ad-hoc signature for local development. That verifies
bundle integrity, but does not make a downloaded application trusted by
Gatekeeper. Public distribution requires a **Developer ID Application** certificate
and Apple notarization. Apple Development and Apple Distribution certificates do
not replace Developer ID Application for this purpose.

Keep the certificate's private key in the local macOS Keychain. The build uses it
in place; it does not export a `.p12` or upload a private key to GitHub.

1. In Xcode Settings → Apple Accounts, select the intended team, then Manage
   Certificates → + → Developer ID Application. Verify the local identity:

   ```sh
   security find-identity -v -p codesigning
   ```

2. Create an app-specific password at [Apple Account](https://account.apple.com/)
   under Sign-In and Security. Store it with the interactive command below. Enter
   the password only at the secure terminal prompt; do not put it in a command,
   source file, shell history, or chat:

   ```sh
   xcrun notarytool store-credentials capacity-watcher-notary \
     --apple-id your-apple-id@example.com --team-id YOUR_TEAM_ID
   ```

3. Build on the Mac containing that certificate and Keychain profile:

   ```sh
   MACOS_SIGN_IDENTITY='Developer ID Application: Your Name (YOUR_TEAM_ID)' \
   MACOS_NOTARY_PROFILE=capacity-watcher-notary \
   sh packaging/build-macos.sh
   ```

   A certificate's SHA-1 fingerprint can replace its full name. `APP_VERSION`
   can override the version; otherwise the build reads the version used by the
   existing release workflow from `packaging/windows-installer.wxs`.

The build signs nested code with hardened runtime and a secure timestamp,
notarizes and staples the application, then creates, signs, notarizes, and staples
the DMG. It checks Gatekeeper acceptance of both the DMG and the app copied into
it. The ZIP contains the stapled application. Final DMG/ZIP files are updated
only after the requested checks succeed. Without `MACOS_NOTARY_PROFILE`, a
build remains a local build and does not claim notarization success.

Notarization can take time. Submission IDs and reports are saved under
`build/notarization/`; uploaded archives stay under `build/macos-staging/`.
After a timeout, resume packaging without rebuilding the app:

```sh
MACOS_SIGN_IDENTITY='Developer ID Application: Your Name (YOUR_TEAM_ID)' \
MACOS_NOTARY_PROFILE=capacity-watcher-notary \
python3 packaging/package_macos.py
```

This reuses a saved submission for identical uploaded bytes. A rejected submission
stops packaging and saves Apple's diagnostic log. Fix its reported issue and
rebuild before submitting again. Use the same Python environment as the build
(including `dmgbuild` and PySide6).

Only upload the finished `.dmg` and `.zip` to Releases and update their checksums.
The existing CI workflow, without these local signing credentials, still produces
development packages; do not overwrite notarized release assets with those files.
macOS may still show the normal first-launch confirmation for an app downloaded
from the internet even after notarization.

References: [Developer ID certificates](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/),
[Apple notarization](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow),
[App-specific passwords](https://support.apple.com/en-us/102654).

## 中文

默认构建使用供本地开发的临时签名（ad-hoc）。包完整性校验通过，并不代表通过
Gatekeeper 安全验证。公开分发需要 **Developer ID Application** 证书和 Apple
公证；Apple Development、Apple Distribution 证书不能替代它。

在 Xcode 设置 → Apple Accounts 中选中正确团队，再通过 Manage Certificates
→ + 创建 Developer ID Application 证书。私钥保留在本机钥匙串，构建直接调用
它签名，无需导出 `.p12` 或上传 GitHub。

在 [Apple 账号](https://account.apple.com/)的“登录与安全 → App 专用密码”中生成
公证密码，然后运行上面的 `notarytool store-credentials` 命令。请将示例中的
Apple ID 和 Team ID 换成自己的值，仅在终端的安全密码提示中输入密码。

设置 `MACOS_SIGN_IDENTITY` 和 `MACOS_NOTARY_PROFILE` 后运行构建命令：前者是
完整证书名称或 SHA-1 指纹，后者是刚保存的钥匙串配置名称。`APP_VERSION` 可覆盖
应用版本号；默认与现有发布流程使用的 MSI 版本一致，不再显示 `0.0.0`。

构建会依次完成应用签名、公证、附加公证票据，以及 DMG 签名、公证、附加票据，
最后验证 DMG 和其中应用的 Gatekeeper 接受状态。ZIP 同样包含附有票据的应用。
缺少公证配置时仍可构建本地开发包，但不会显示公证成功。

公证等待超时后，无需重建应用，使用相同环境变量运行
`python3 packaging/package_macos.py`，会复用已上传文件的提交编号。
提交记录和诊断日志位于 `build/notarization/`，待处理文件保存在
`build/macos-staging/`。Apple 拒绝公证时流程会停止，需要根据日志修复后重新构建。

发布时只上传最终 DMG/ZIP 并更新校验值。没有配置签名凭据的现有 CI 仍会生成
开发包，不能用它覆盖已公证的发布附件。公证通过后，macOS 首次打开互联网下载的
应用时仍可能显示正常的打开确认提示。
