class ComLinkError(Exception):
    pass

class ComLinkTimeout(ComLinkError):
    pass

class ComLinkCRCError(ComLinkError):
    pass