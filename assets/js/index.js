import CTFd from "@ctfdio/ctfd-js";

import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";

import highlight from "./theme/highlight";
import styles from "./theme/styles";
import times from "./theme/times";

import alerts from "./utils/alerts";
import collapse from "./utils/collapse";
import tooltips from "./utils/tooltips";

import eventAlerts from "./utils/notifications/alerts";
import eventRead from "./utils/notifications/read";
import eventToasts from "./utils/notifications/toasts";

import "./components/language";

dayjs.extend(advancedFormat);
CTFd.init(window.init);

(() => {
  styles();
  times();
  highlight();

  alerts();
  tooltips();
  collapse();

  eventRead();
  eventAlerts();
  eventToasts();
})();

export default CTFd;
