import logging

import aiohttp

logger = logging.getLogger(__name__)


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


async def get_github_issues(per_page=100):
    url = f"https://api.github.com/repos/neverscapealone/never-scape-alone/issues?per_page={per_page}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            response = await resp.json()
    return response


async def issues_to_response(data) -> list:
    payload = list()
    for issue_dict in data:
        d = dict()
        issue = AttrDict(issue_dict)
        points = 0
        for label in issue.labels:
            label_name = label["name"]
            count = label_name[: label_name.find("-")]
            points += int(count)
        l = [(issue.title, issue.url), points]
        payload.append(l)
    sorted_payload = sorted(payload, reverse=True, key=lambda x: x[1])

    response = list()
    for title, points in sorted_payload:
        d = dict()
        d["title"] = title[0]
        d["url"] = title[1]
        d["priority"] = points
        response.append(d)
    return response
