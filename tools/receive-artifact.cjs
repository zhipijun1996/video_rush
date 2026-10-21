// A GitHub-hosted job receives one already-rendered ZIP directly in its Artifact
// storage. Runtime tokens stay on the runner. The scoped upload URL is encrypted
// to the cloud producer's one-time public key before appearing in the check.
const crypto = require('node:crypto');
const path = require('node:path');

module.exports = async function ({github, context, core}) {
  const base = path.join(process.env.GITHUB_WORKSPACE, 'build/artifact-bridge/node_modules/@actions/artifact/lib');
  const {internalArtifactTwirpClient} = require(base + '/internal/shared/artifact-twirp-client.js');
  const {getBackendIdsFromToken} = require(base + '/internal/shared/util.js');
  const {StringValue} = require(base + '/generated/index.js');
  const name = process.env.VR_ARTIFACT_NAME;
  const size = Number(process.env.VR_BYTE_SIZE);
  const hash = process.env.VR_ZIP_SHA256;
  if (!/^[A-Za-z0-9_-]{1,80}$/.test(name) || !Number.isSafeInteger(size) || size <= 0 ||
      size > 2 * 1024 ** 3 || !/^[a-f0-9]{64}$/.test(hash)) throw new Error('Invalid delivery metadata');
  const publicKey = Buffer.from(process.env.VR_PUBLIC_KEY, 'base64').toString('utf8');
  const client = internalArtifactTwirpClient();
  const ids = getBackendIdsFromToken();
  const created = await client.CreateArtifact({...ids, name, version: 4,
    expiresAt: {seconds: String(Math.floor(Date.now() / 1000) + 14 * 86400), nanos: 0}});
  if (!created.ok) throw new Error('Artifact creation failed');
  const url = created.signedUploadUrl;
  core.setSecret(url);
  const key = crypto.randomBytes(32), nonce = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, nonce);
  const ciphertext = Buffer.concat([cipher.update(url, 'utf8'), cipher.final()]);
  const capsule = Buffer.from(JSON.stringify({
    key: crypto.publicEncrypt({key: publicKey, oaepHash: 'sha256', padding: crypto.constants.RSA_PKCS1_OAEP_PADDING}, key).toString('base64'),
    nonce: nonce.toString('base64'), data: Buffer.concat([ciphertext, cipher.getAuthTag()]).toString('base64')
  })).toString('base64');
  const {owner, repo} = context.repo;
  const jobs = await github.rest.actions.listJobsForWorkflowRun({owner, repo, run_id: context.runId});
  const job = jobs.data.jobs.find(j => j.name === 'Receive verified episode');
  if (!job) throw new Error('Cannot identify delivery job check');
  const check_run_id = Number(job.check_run_url.split('/').pop());
  await github.rest.checks.update({owner, repo, check_run_id, output: {
    title: 'Waiting for the verified movie package',
    summary: 'VR_CAPSULE:' + capsule + '\n\nOnly the cloud producer holds the matching private key.'
  }});
  // The upload SAS permits reading its blob properties. No bearer token leaves
  // this job. Publish only after the whole ZIP exists at the expected size.
  const deadline = Date.now() + 10 * 60 * 1000;
  let ready = false;
  while (Date.now() < deadline) {
    const response = await fetch(url, {method: 'HEAD'});
    if (response.ok && Number(response.headers.get('content-length')) === size) {ready = true; break;}
    if (![404, 200].includes(response.status)) throw new Error('Artifact storage probe failed: ' + response.status);
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  if (!ready) throw new Error('Timed out waiting for ZIP upload; no successful delivery claimed');
  const finalized = await client.FinalizeArtifact({...ids, name, size: String(size), hash: StringValue.create({value: 'sha256:' + hash})});
  if (!finalized.ok) throw new Error('Artifact finalization failed');
  const link = `${context.serverUrl}/${owner}/${repo}/actions/runs/${context.runId}/artifacts/${finalized.artifactId}`;
  await github.rest.checks.update({owner, repo, check_run_id, output: {
    title: 'Movie, cover and submission materials ready',
    summary: `[Download the complete episode ZIP](${link})\n\nSHA256: \`${hash}\`\n\n14-day retention. Technical checks passed locally; human phone review remains pending.`
  }});
  await core.summary.addHeading('成片下载').addLink('下载成片、封面与标题简介 ZIP', link)
    .addRaw('\n\n复用已验收成片，包含指定BGM；未重新渲染。Artifact保留14天，完整试听与审美待用户审核。\n').write();
  core.info('Artifact finalized: ' + finalized.artifactId);
};
