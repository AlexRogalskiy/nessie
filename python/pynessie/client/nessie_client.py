# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Dremio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Main module."""

from typing import Any
from typing import cast
from typing import Generator
from typing import Optional

import confuse

from ._endpoints import all_references
from ._endpoints import assign_branch
from ._endpoints import assign_tag
from ._endpoints import cherry_pick
from ._endpoints import commit
from ._endpoints import create_reference
from ._endpoints import delete_branch
from ._endpoints import delete_tag
from ._endpoints import get_content
from ._endpoints import get_default_branch
from ._endpoints import get_diff
from ._endpoints import get_reference
from ._endpoints import list_logs
from ._endpoints import list_tables
from ._endpoints import merge
from ..auth import setup_auth
from ..model import Branch
from ..model import CommitMeta
from ..model import Content
from ..model import ContentKey
from ..model import ContentSchema
from ..model import DiffResponse
from ..model import DiffResponseSchema
from ..model import Entries
from ..model import EntriesSchema
from ..model import LogEntry
from ..model import LogResponse
from ..model import LogResponseSchema
from ..model import Merge
from ..model import MergeSchema
from ..model import MultiContents
from ..model import MultiContentSchema
from ..model import Operation
from ..model import Reference
from ..model import ReferenceSchema
from ..model import ReferencesResponse
from ..model import ReferencesResponseSchema
from ..model import Tag
from ..model import Transplant
from ..model import TransplantSchema


class NessieClient:
    """Base Nessie Client."""

    def __init__(self: "NessieClient", config: confuse.Configuration) -> None:
        """Create a Nessie Client from known config."""
        self._base_url = config["endpoint"].get()
        self._ssl_verify = config["verify"].get(bool)
        self._auth = setup_auth(config)
        self._commit_id: str = cast(str, None)

        try:
            self._base_branch = config["default_branch"].get()
        except confuse.exceptions.NotFoundError:
            self._base_branch = None

    def list_references(self: "NessieClient", fetch_all: bool = False) -> ReferencesResponse:
        """Fetch all known references.

        :return: list of Nessie References
        """
        references = all_references(self._base_url, self._auth, self._ssl_verify, fetch_all)
        return ReferencesResponseSchema().load(references)

    def get_reference(self: "NessieClient", name: Optional[str]) -> Reference:
        """Fetch a ref.

        :param name: name of ref to fetch
        :return: Nessie reference
        """
        ref_obj = (
            get_reference(self._base_url, self._auth, name, self._ssl_verify)
            if name
            else get_default_branch(self._base_url, self._auth, self._ssl_verify)
        )
        ref = ReferenceSchema().load(ref_obj)
        return ref

    def create_branch(self: "NessieClient", branch: str, ref: str = None, hash_on_ref: str = None) -> Branch:
        """Create a branch.

        :param branch: name of new branch to create
        :param ref: branch or tag to fork from ('hash_on_ref' should be reachable from this reference)
        :param hash_on_ref: hash to assign 'branch' to
        :return: Nessie branch object
        """
        ref_json = ReferenceSchema().dump(Branch(branch, hash_on_ref))
        ref_obj = create_reference(self._base_url, self._auth, ref_json, ref, self._ssl_verify)
        return cast(Branch, ReferenceSchema().load(ref_obj))

    def delete_branch(self: "NessieClient", branch: str, hash_: str) -> None:
        """Delete a branch.

        :param branch: name of branch to delete
        :param hash_: hash of the branch
        """
        delete_branch(self._base_url, self._auth, branch, hash_, self._ssl_verify)

    def create_tag(self: "NessieClient", tag: str, ref: str, hash_on_ref: str = None) -> Tag:
        """Create a tag.

        :param tag: name of new tag to create
        :param ref: name of the reference via which 'hash_on_ref' is reachable
        :param hash_on_ref: hash to assign 'branch' to
        :return: Nessie tag object
        """
        ref_json = ReferenceSchema().dump(Tag(tag, hash_on_ref) if hash_on_ref else Tag(tag))
        ref_obj = create_reference(self._base_url, self._auth, ref_json, ref, self._ssl_verify)
        return cast(Tag, ReferenceSchema().load(ref_obj))

    def delete_tag(self: "NessieClient", tag: str, hash_: str) -> None:
        """Delete a tag.

        :param tag: name of tag to delete
        :param hash_: hash of the branch
        """
        delete_tag(self._base_url, self._auth, tag, hash_, self._ssl_verify)

    def list_keys(
        self: "NessieClient",
        ref: str,
        hash_on_ref: str = None,
        max_result_hint: Optional[int] = None,
        page_token: Optional[str] = None,
        query_filter: Optional[str] = None,
    ) -> Entries:
        """Fetch a list of all tables from a known branch.

        :param ref: name of branch
        :param hash_on_ref: hash on reference
        :param entity_types: list of types to filter keys on
        :param query_filter: A CEL expression that allows advanced filtering capabilities
        :return: list of Nessie table names
        """
        return EntriesSchema().load(
            list_tables(self._base_url, self._auth, ref, hash_on_ref, max_result_hint, page_token, query_filter, self._ssl_verify)
        )

    def get_content(self: "NessieClient", ref: str, content_key: ContentKey, hash_on_ref: Optional[str] = None) -> Content:
        """Fetch a content from a known ref.

        :param ref: name of ref
        :param hash_on_ref: hash on reference
        :param content_key: content key to fetch
        :return: A single content
        """
        return ContentSchema().load(get_content(self._base_url, self._auth, ref, content_key, hash_on_ref, self._ssl_verify))

    def commit(
        self: "NessieClient", branch: str, old_hash: str, reason: Optional[str] = None, author: Optional[str] = None, *ops: Operation
    ) -> Branch:
        """Modify a set of Nessie tables."""
        meta = CommitMeta(message=reason if reason else "")
        if author:
            meta.author = author
        ref_obj = commit(self._base_url, self._auth, branch, MultiContentSchema().dumps(MultiContents(meta, list(ops))), old_hash)
        return cast(Branch, ReferenceSchema().load(ref_obj))

    def assign_branch(self: "NessieClient", branch: str, to_ref: str, to_ref_hash: str = None, old_hash: Optional[str] = None) -> None:
        """Assign a hash to a branch."""
        if not old_hash:
            old_hash = self.get_reference(branch).hash_
        assert old_hash is not None
        ref_json = ReferenceSchema().dumps(Branch(to_ref, to_ref_hash) if to_ref_hash else Branch(to_ref))
        assign_branch(self._base_url, self._auth, branch, ref_json, old_hash, self._ssl_verify)

    def assign_tag(self: "NessieClient", tag: str, to_ref: str, to_ref_hash: str = None, old_hash: Optional[str] = None) -> None:
        """Assign a hash to a tag."""
        if not old_hash:
            old_hash = self.get_reference(tag).hash_
        assert old_hash is not None
        ref_json = ReferenceSchema().dumps(Tag(to_ref, to_ref_hash) if to_ref_hash else Tag(to_ref))
        assign_tag(self._base_url, self._auth, tag, ref_json, old_hash, self._ssl_verify)

    def merge(
        self: "NessieClient", from_ref: str, onto_branch: str, from_hash: Optional[str] = None, old_hash: Optional[str] = None
    ) -> None:
        """Merge a branch into another branch."""
        if not old_hash:
            old_hash = self.get_reference(onto_branch).hash_
        assert old_hash is not None
        if not from_hash:
            from_hash = self.get_reference(from_ref).hash_
        merge_json = MergeSchema().dump(Merge(from_ref, str(from_hash)))
        merge(self._base_url, self._auth, onto_branch, merge_json, old_hash, self._ssl_verify)

    def cherry_pick(self: "NessieClient", branch: str, from_ref: str, old_hash: Optional[str] = None, *hashes: str) -> None:
        """Cherry pick a list of hashes to a branch."""
        if not old_hash:
            old_hash = self.get_reference(branch).hash_
        assert old_hash is not None
        transplant_json = TransplantSchema().dump(Transplant(from_ref, list(hashes)))
        cherry_pick(self._base_url, self._auth, branch, transplant_json, old_hash, self._ssl_verify)

    def get_log(
        self: "NessieClient",
        start_ref: str,
        hash_on_ref: Optional[str] = None,
        max_records: Optional[int] = None,
        fetch_all: bool = False,
        **filtering_args: Any
    ) -> Generator[LogEntry, Any, None]:
        """Fetch all logs starting at start_ref.

        start_ref can be any ref.

        Note:
            this will load the log into local memory and filter at the client. Currently there are no
            primitives in the REST api to limit logs or perform paging. TODO
        """
        page_token = filtering_args.get("pageToken", None)

        def fetch_logs(fetch_max: Optional[int], token: Optional[str] = page_token) -> LogResponse:
            if token:
                filtering_args["pageToken"] = token

            fetched_logs = list_logs(
                base_url=self._base_url,
                auth=self._auth,
                hash_on_ref=hash_on_ref,
                ref=start_ref,
                ssl_verify=self._ssl_verify,
                max_records=fetch_max,
                fetch_all=fetch_all,
                **filtering_args
            )
            parsed_logs = LogResponseSchema().load(fetched_logs)
            return parsed_logs

        log_response = fetch_logs(fetch_max=max_records)

        def generator(logs: LogResponse, fetch_max: Optional[int]) -> Generator[LogEntry, Any, None]:
            while True:
                for log in logs.log_entries:
                    yield log
                    if fetch_max is not None:
                        fetch_max -= 1
                        if fetch_max <= 0:
                            # yield only the requierd number of results, if server returns more records than expected.
                            break
                if not logs.has_more or (fetch_max is not None and fetch_max <= 0):
                    break
                logs = fetch_logs(fetch_max=fetch_max, token=logs.token)

        return generator(log_response, max_records)

    def get_default_branch(self: "NessieClient") -> str:
        """Fetch default branch either from config if specified or from the server."""
        return self._base_branch if self._base_branch else self.get_reference(None).name

    def get_base_url(self: "NessieClient") -> str:
        """Return Nessie server configured base URL."""
        return self._base_url

    def get_diff(
        self: "NessieClient",
        from_ref: str,
        to_ref: str,
    ) -> DiffResponse:
        """Retrieve the diff between from_ref and to_ref.

        from_ref / to_ref can be any ref.
        """
        return DiffResponseSchema().load(get_diff(self._base_url, self._auth, from_ref, to_ref, self._ssl_verify))
