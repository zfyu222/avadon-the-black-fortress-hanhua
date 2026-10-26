"""Verify the public stable release and download its ZIP without credentials."""
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path
from build_release import P,DISPATCH,ARCHIVE,RELEASE,sha,write

def api(path):
    result=subprocess.run(['gh','api',path],check=True,capture_output=True)
    return json.loads(result.stdout)

def main():
    repository='zfyu222/avadon-the-black-fortress-hanhua'
    repo=api('repos/'+repository)
    release=api('repos/'+repository+'/releases/latest')
    assert not repo['private'] and release['tag_name']=='v1.0' and not release['draft'] and not release['prerelease']
    assert release['html_url']==RELEASE
    matches=[a for a in release['assets'] if a['name'] in (ARCHIVE.name,'Avadon_The_Black_Fortress_1.0.zip')]
    if not matches:
        assert len(release['assets'])==1 and release['assets'][0]['size']==ARCHIVE.stat().st_size
        candidate=release['assets'][0]
        metadata=P/'Release/github_asset_metadata.json'
        write(metadata,dict(name='Avadon_The_Black_Fortress_1.0.zip',label=ARCHIVE.name))
        changed=subprocess.run(['gh','api','repos/'+repository+'/releases/assets/'+str(candidate['id']),
            '--method','PATCH','--input',str(metadata)],check=True,capture_output=True)
        asset=json.loads(changed.stdout)
        assert asset['name']=='Avadon_The_Black_Fortress_1.0.zip' and asset['label']==ARCHIVE.name
    else:asset=matches[0]
    assert asset['state']=='uploaded' and asset['size']==ARCHIVE.stat().st_size
    url=asset['browser_download_url']
    assert url.startswith('https://github.com/'+repository+'/releases/download/v1.0/')
    directory=DISPATCH/'Verification/download';directory.mkdir(parents=True,exist_ok=True)
    downloaded=directory/ARCHIVE.name
    request=urllib.request.Request(url,headers={'User-Agent':'Avadon-localization-release-check'})
    with urllib.request.urlopen(request,timeout=90) as response, downloaded.open('wb') as stream:
        assert response.status==200
        while chunk:=response.read(1024*1024):stream.write(chunk)
    assert sha(downloaded)==sha(ARCHIVE)
    result=dict(status='passed',repository=repo['html_url'],public=True,release_url=release['html_url'],tag=release['tag_name'],
        latest_stable=True,draft=False,prerelease=False,published_at=release['published_at'],asset_id=asset['id'],
        asset_name=asset['name'],asset_bytes=asset['size'],asset_url=url,anonymous_download_verified=True,
        asset_display_label=asset.get('label'),local_archive_name=ARCHIVE.name,
        filename_note='GitHub normalizes this Chinese filename; the download uses an ASCII alias and the required Chinese name remains its display label and local ZIP name.',
        downloaded_sha256=sha(downloaded),local_sha256=sha(ARCHIVE))
    write(DISPATCH/'GITHUB_RELEASE_VERIFICATION.json',result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
