import pytest
from video_rush.posting_policy import public_description, contains_git_site, require_public_copy
from video_rush.publish import posting_copy


def test_removes_git_source_block_preserving_text_topic_and_game_short_link():
    raw=('正文与AI配音说明。\n\n口播、层级结构与来源：\n'
         'https://github.com/me/project\n游戏：https://me.github.io/game/\n'
         '试玩：https://b23.tv/example\n#B站AI创造公开赛#')
    clean=public_description(raw)
    assert clean=='正文与AI配音说明。\n\n试玩：https://b23.tv/example\n#B站AI创造公开赛#'
    assert not contains_git_site(clean)


def test_inline_credit_survives_removal_and_non_git_sources_are_unchanged():
    raw='火柴人、剪辑与主题配乐由Video Rush制作；含短动漫引用。制作与素材说明：https://github.com/me/docs'
    assert public_description(raw)=='火柴人、剪辑与主题配乐由Video Rush制作；含短动漫引用。'
    other='Git管理经验。作者许可：https://example.org/license'
    assert public_description(other)==other


@pytest.mark.parametrize('url',['https://google.github.io/x','github.com/user/repo','https://gitlab.com/u/r','https://raw.githubusercontent.com/u/r/main/x'])
def test_git_hosts_blocked_in_public_copy(url):
    assert contains_git_site(url)
    with pytest.raises(ValueError):require_public_copy(url)


def test_posting_output_filters_description_but_does_not_rewrite_evidence():
    spec={'title':'真实冲突标题','title_candidates':[],'evidence':[{'url':'https://github.com/u/r'}]}
    copy=posting_copy(spec,'开发记录。\n源码：https://github.com/u/r\n#B站AI创造公开赛#')
    assert 'github' not in copy
    assert spec['evidence'][0]['url']=='https://github.com/u/r'
