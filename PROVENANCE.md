# Official asset provenance

このリポジトリの公式素材は、ファイル名や通常の画像 metadata だけを根拠に
「公式」と判定しません。

## 現在の真正性レイヤー

1. `provenance/assets.json` が公式素材の安定した asset ID、ライセンス、
   原本との関係を列挙します。
2. `tools/generate_asset_manifest.py` が各ファイルの SHA-256、サイズ、
   source repository、Git commit SHA を含む `assets-manifest.json` と
   `SHA256SUMS` を生成します。
3. `.github/workflows/provenance.yml` が main / release でそれらを生成し、
   GitHub OIDC + Sigstore を利用する GitHub Artifact Attestations で、
   manifest と各公式素材の digest を署名します。
4. metadata が削除されても、ローカルファイルの digest を GitHub 上の
   attestation と照合できます。

長期秘密鍵はこのリポジトリへコミットせず、GitHub Actions の短命 OIDC
credential を利用します。

## 検証

GitHub CLI が利用できる場合、公式素材を次のように検証できます。

```bash
gh attestation verify <asset-file> --repo tomiya7688/super_icon_license
```

より厳密に signer workflow も固定する場合:

```bash
gh attestation verify <asset-file> \
  --repo tomiya7688/super_icon_license \
  --signer-workflow tomiya7688/super_icon_license/.github/workflows/provenance.yml
```

CI が生成した provenance artifact をダウンロードした場合は、
`assets-manifest.json` 自体も同じ方法で検証できます。

## ローカルで manifest を再生成

```bash
python3 tools/generate_asset_manifest.py \
  --repository tomiya7688/super_icon_license \
  --revision "$(git rev-parse HEAD)" \
  --output /tmp/assets-manifest.json \
  --checksums /tmp/SHA256SUMS
```

## C2PA / Content Credentials

C2PA Tool は埋め込み manifest と外部 `.c2pa` sidecar の両方を扱えるため、
画像形式ごとの Content Credentials レイヤーとして有力です。

ただし、**production 用の C2PA signing credential / trust chain をまだ
このリポジトリには設定していません。** 信頼されない自己署名証明書を
「公式署名」として配ることはしません。

そのため現時点の暗号学的な公式判定は GitHub Artifact Attestation を正とし、
C2PA 埋め込みは production credential が確定してから追加します。
