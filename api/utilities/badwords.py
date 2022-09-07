# words are taken from better_profanity's list of bad words and modififed
# large swaths of words were taken out, and some words may have been missed, an effort was made to retain the most highly offensive words
# as they'll be censored regardless, and could be used to trigger plugin bans.
# If you have suggestions to this list, please submit a PR titled "Adds Bad Words" on the NeverScapeAlone-API
# Thank you!


class BadWords:
    """a set of bad words that will be censored in chat and on the notes section"""

    def __init__(self):
        self.bad_words = {
            "chink",
            "dyke",
            "dykes",
            "fag",
            "fagg",
            "fagged",
            "fagging",
            "faggit",
            "faggitt",
            "faggot",
            "faggs",
            "fagot",
            "fagots",
            "fags",
            "faig",
            "faigt",
            "incest",
            "kike",
            "kikes",
            "kyke",
            "nword",
            "n1g",
            "n1gg",
            "n1gga",
            "n1gger",
            "negro",
            "nig",
            "nigg",
            "nigg3r",
            "nigg4h",
            "nigga",
            "niggah",
            "niggas",
            "niggaz",
            "nigger",
            "niggers",
            "niggle",
            "niglet",
            "nympho",
            "pedo",
            "pedophile",
            "pedophilia",
            "pedophiliac",
            "queef",
            "queer",
            "queero",
            "queers",
            "r-tard",
            "reetard",
            "retard",
            "retarded",
            "ritard",
            "rtard",
            "spic",
            "spick",
            "spik",
            "spiks",
            "w00se",
            "wetback",
            "whitey",
            "wigger",
        }
