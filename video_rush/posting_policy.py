"""Audience-facing posting preferences; internal evidence URLs remain intact."""
import re

GIT_SITE = re.compile(
    r'(?<![\w.-])(?:(?:https?:)?//)?(?:[a-z0-9-]+\.)*'
    r'(?:github\.com|github\.io|githubusercontent\.com|gitlab\.com|gitlab\.io|'
    r'gitee\.com|gitee\.io|gitcode\.com|gitcode\.net|bitbucket\.org|codeberg\.org|git\.sr\.ht)'
    r'(?![\w.-])(?:/[^\s<>()[\]{}，。；！？（）]*)?', re.I)
LABEL = r'(?:源码|代码仓库|仓库|游戏|模块库|地图生成器|补充阅读|制作与来源|材料与出处|制作与素材说明|口播、层级结构与来源|完整来源|来源)'


def contains_git_site(text):
    return bool(GIT_SITE.search(text))


def public_description(text):
    """Remove Git website references, retaining narration/AI/credit text.

    Other URLs and the word Git itself are not prohibited. Do not follow or
    rewrite unrelated short links. Source manifests are never passed here.
    """
    if not contains_git_site(text):
        return text.strip()
    lines=[]
    for raw in text.splitlines():
        line=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                    lambda m:m[1] if contains_git_site(m[2]) else m[0],raw)
        had_git=contains_git_site(line)
        line=GIT_SITE.sub('',line).rstrip()
        if had_git:
            # Keep any preceding sentence (e.g. attribution), remove its now
            # empty trailing source label and URL-only parenthetic notes.
            line=re.sub(LABEL+r'\s*[:：]\s*$', '',line).rstrip()
            line=re.sub(r'\s*[（(](?:制作时首页404[^）)]*)[）)]\s*$', '',line).rstrip()
        if re.fullmatch(r'\s*(?:[-*]\s*)?'+LABEL+r'\s*[:：]?\s*',line):
            continue
        if had_git and not line.strip(' \t-*:：。;；'):
            continue
        lines.append(line)
    result=re.sub(r'\n{3,}','\n\n','\n'.join(lines)).strip()
    if contains_git_site(result):raise ValueError('Public description still contains a Git website')
    return result


def require_public_copy(*texts):
    if any(contains_git_site(text) for text in texts):
        raise ValueError('User prohibits Git websites in public posting materials')
