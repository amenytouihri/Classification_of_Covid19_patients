import urllib


def build_url(base_url, path, args_dict=None):
    # Returns a list in the structure of urlparse.ParseResult
    url_parts = list(urllib.parse.urlparse(base_url))
    url_parts[2] = path
    if (args_dict):
        url_parts[4] = urllib.parse.urlencode(
            args_dict, quote_via=urllib.parse.quote)
    return urllib.parse.urlunparse(url_parts)
