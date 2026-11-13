const reportUrl = process.env.ALLURE_REPORT_URL;

const config = {
  name: "Agent project API",
  output: "./allure-report",
  historyPath: "./history.jsonl",
};

if (reportUrl) {
  config.historyBaseUrl = reportUrl;
}

export default config;
