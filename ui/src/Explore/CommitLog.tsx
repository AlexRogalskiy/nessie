/*
 * Copyright (C) 2020 Dremio
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Button, Card, Nav } from "react-bootstrap";
import moment from "moment";
import React, { useEffect, useState, Fragment } from "react";
import { useParams, useHistory, useLocation, Redirect } from "react-router-dom";
import { api, LogEntry, LogResponse } from "../utils";
import { factory } from "../ConfigLog4j";
import CodeIcon from "@material-ui/icons/Code";
import "./CommitLog.css";
import { Icon, Tooltip, TablePagination } from "@material-ui/core";
import ExploreLink from "./ExploreLink";
import { routeSlugs } from "./Constants";
import { EmptyMessageView } from "./Components";
import CommitDetails from "./CommitDetails";
import { Location, History } from "history";

const log = factory.getLogger("api.CommitHeader");

const fetchLog = (
  ref: string,
  maxRecords: number,
  pageToken = ""
): Promise<void | LogResponse | undefined> => {
  const params = pageToken
    ? { ref, maxRecords, pageToken }
    : { ref, maxRecords };
  return api()
    .getCommitLog(params)
    .then((data) => {
      return data;
    })
    .catch((t) => log.error("CommitLog", t));
};

const CommitLog = (props: {
  currentRef: string;
  path: string[];
}): React.ReactElement => {
  const { currentRef, path } = props;
  const { slug } = useParams<{ slug: string }>();
  const [logList, setLogList] = useState<LogEntry[]>([
    {
      commitMeta: {
        author: undefined,
        authorTime: undefined,
        commitTime: undefined,
        committer: undefined,
        hash: undefined,
        message: "",
        properties: {},
        signedOffBy: undefined,
      },
    },
  ]);
  const [showCommitDetails, setShowCommitDetails] = useState(false);
  const [commitDetails, setCommitDetails] = useState<LogEntry | undefined>();
  const [isRefNotFound, setRefNotFound] = useState(false);
  const [hasMoreLog, setHasMoreLog] = useState<LogResponse["hasMore"]>(false);
  const [paginationToken, setPaginationToken] =
    useState<LogResponse["token"]>();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const location = useLocation() as Location;
  const history = useHistory() as History;

  const fetchMoreLog = async (isResetData = false) => {
    const pageToken = isResetData ? "" : paginationToken;
    const fetchLogResults = await fetchLog(currentRef, rowsPerPage, pageToken);
    if (fetchLogResults) {
      const { hasMore, token } = fetchLogResults;
      const logEntries =
        fetchLogResults.logEntries && fetchLogResults.logEntries.length > 0
          ? fetchLogResults.logEntries
          : [];
      const dataList = isResetData ? logEntries : logList.concat(logEntries);
      setLogList(dataList);
      setRefNotFound(false);
      setHasMoreLog(hasMore);
      setPaginationToken(token);
    }
  };
  useEffect(() => {
    const logs = async () => {
      const fetchLogResults = await fetchLog(currentRef, rowsPerPage);
      if (fetchLogResults) {
        const { hasMore, token } = fetchLogResults;
        const logEntries =
          fetchLogResults.logEntries && fetchLogResults.logEntries.length > 0
            ? fetchLogResults.logEntries
            : [];
        setLogList(logEntries);
        setRefNotFound(false);
        setHasMoreLog(hasMore);
        setPaginationToken(token);
        setPage(0);
      }
      setRefNotFound(fetchLogResults === undefined);
      if (showCommitDetails) {
        const listPath = location.pathname.substring(
          0,
          location.pathname.lastIndexOf("/")
        );
        history.push(listPath);
      }
    };
    void logs();
  }, [currentRef, rowsPerPage]);

  useEffect(() => {
    if (slug && !isRefNotFound) {
      const last = slug.substring(slug.lastIndexOf("/") + 1, slug.length);
      setShowCommitDetails(last !== routeSlugs.commits);
      const logDetails = logList.find((logItem) => {
        return logItem.commitMeta && logItem.commitMeta.hash === last;
      });
      setCommitDetails(logDetails);
    }
  }, [slug, logList]);

  if (isRefNotFound) {
    return <Redirect to="/notfound" />;
  }

  if (!logList || logList.length === 0 || !logList[0].commitMeta.hash) {
    return <EmptyMessageView />;
  }

  const copyHash = async (hashCode: string) => {
    await navigator.clipboard.writeText(hashCode);
  };
  const commitList = (currentLog: LogEntry, index: number) => {
    const { commitTime, author, message, hash } = currentLog.commitMeta;
    const hoursDiff = moment().diff(moment(commitTime), "hours");
    const dateTimeAgo =
      hoursDiff > 24
        ? moment(commitTime).format("YYYY-MM-DD, hh:mm a")
        : `${moment(commitTime).fromNow()}`;

    return (
      <Fragment key={index}>
        <Card.Body className="commitLog__body border-bottom">
          <div>
            <Nav.Item>
              <ExploreLink
                toRef={currentRef}
                path={path.concat(hash ?? "#")}
                type="CONTAINER"
                className="commitLog__messageLink"
              >
                {message}
              </ExploreLink>
            </Nav.Item>
            <Card.Text className={"ml-3"}>
              {author}
              <span className={"ml-2"}>committed on</span>
              <span className={"ml-2"}>{dateTimeAgo}</span>
            </Card.Text>
          </div>
          <div className={"commitLog__btnWrapper"}>
            <div className={"border rounded commitLog__hashBtnWrapper"}>
              <Tooltip title="Copy hash">
                <Button
                  className="border-right commitLog__copyBtn rightBtnHover"
                  variant="link"
                  onClick={() => copyHash(hash || "")}
                >
                  <Icon>content_copy</Icon>
                </Button>
              </Tooltip>
              <ExploreLink
                toRef={currentRef}
                path={path.concat(hash ?? "#")}
                type="CONTAINER"
                className="commitLog__hashBtn rightBtnHover"
              >
                <Tooltip title="Commit details">
                  <Button variant="link">
                    <span className="font-italic">{hash?.slice(0, 8)}</span>
                  </Button>
                </Tooltip>
              </ExploreLink>
            </div>
            <div>
              <Tooltip title="Browse the repository at this point in the history">
                <Button variant="light" className={"ml-3 rightBtnHover"}>
                  <CodeIcon />
                </Button>
              </Tooltip>
            </div>
          </div>
        </Card.Body>
      </Fragment>
    );
  };

  const handleChangePage = (
    event: React.MouseEvent<HTMLButtonElement> | null,
    newPage: number
  ) => {
    setPage(newPage);
    if (hasMoreLog) {
      void fetchMoreLog();
    }
  };

  const handleChangeRowsPerPage = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const paginator = () => (
    <TablePagination
      component="div"
      count={!hasMoreLog ? logList.length : -1}
      page={page}
      onPageChange={handleChangePage}
      rowsPerPage={rowsPerPage}
      onRowsPerPageChange={handleChangeRowsPerPage}
      SelectProps={{
        id: "commitLogRowPerPageSelect",
        labelId: "commitLogRowPerPageSelectLabel",
      }}
    />
  );

  return (
    <Card className={"commitLog"}>
      {!showCommitDetails ? (
        logList
          .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
          .map((item, index) => {
            return commitList(item, index);
          })
      ) : (
        <CommitDetails commitDetails={commitDetails} currentRef={currentRef} />
      )}
      {!showCommitDetails && paginator()}
    </Card>
  );
};

export default CommitLog;
