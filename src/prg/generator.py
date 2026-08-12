"""The build policy: which tags cross over, and what they become.

Everything here answers a "why" question. Which tags count as releases, what
timestamp each one gets, what order they land in, what the message says.
The "how" of talking to git lives in `gitio.py`.

STATUS: blueprint. Every method below raises. See DESIGN.md for the rules
they will implement.
"""

RELEASE_TAG_PATTERN = "v*"
DEFAULT_TIME = "12:00:00"
DEFAULT_TZ = "local"
DEFAULT_WEED_OUT = "weed-out"


class PRG:
    """Rebuild a public repo from a private one, one commit per release tag."""

    def __init__(
        self,
        source,
        target,
        tz=DEFAULT_TZ,
        time=DEFAULT_TIME,
        author=None,
        weed_out=DEFAULT_WEED_OUT,
        start=None,
        commit=False,
    ):
        """Capture the settings for a single run.

        `commit` is the safety switch. False means report only.
        `author` of None means fall back to the ambient git identity.
        """
        self.source = source
        self.target = target
        self.tz = tz
        self.time = time
        self.author = author
        self.weed_out = weed_out
        self.start = start
        self.commit = commit

    def release_tags(self):
        """Return the v* tags reachable from main/master, oldest first.

        Tags on other branches are skipped, and so are tags that do not match
        the release pattern. `--start` trims the list from the front.
        """
        raise NotImplementedError

    def uniform_timestamp(self, tag_date, ordinal):
        """Return the tag's own date at the uniform time.

        `ordinal` is the tag's position among releases sharing that date. The
        first takes the exact time, the second one second later, and so on, so
        same-day releases keep their order.
        """
        raise NotImplementedError

    def checkout_tag(self, tag, work_dir):
        """Extract the tree at `tag` into a scratch directory.

        The source repo is only ever read. Nothing is checked out in place.
        """
        raise NotImplementedError

    def run_weed_out(self, work_dir):
        """Run the weed-out sanitizer over a scratch tree.

        Invoked as `weed-out delete <work_dir> --commit`, so the tree keeps
        only what the source repo's `.weed-out-ignore` names.
        """
        raise NotImplementedError

    def build_commit(self, tag, timestamp):
        """Commit a sanitized tree into the target repo.

        The message comes from the tag's annotation, falling back to the tag
        name for a lightweight tag. Author and committer dates both take the
        uniform timestamp.
        """
        raise NotImplementedError

    def reconstruct(self):
        """Build the target repo from scratch.

        1. Confirm the source is a git repo and the target does not exist
        2. Collect the release tags, oldest first
        3. For each tag: check out, sanitize, commit at its uniform timestamp
        4. Recreate the tags on the new commits
        5. Expire the reflog and prune unreachable objects
        """
        raise NotImplementedError

    def cleanup(self):
        """Expire the reflog and prune unreachable objects.

        Housekeeping, not the security guarantee. Nothing unsanitized ever
        enters the target's object store to begin with.
        """
        raise NotImplementedError

    def inspect(self):
        """Report the tags that would become commits, with their timestamps."""
        raise NotImplementedError
