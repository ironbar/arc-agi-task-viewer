const DATASETS = {
  arc1Training: "ARC-AGI-1 training",
  arc1Evaluation: "ARC-AGI-1 evaluation",
  arc2Training: "ARC-AGI-2 training",
  arc2Evaluation: "ARC-AGI-2 evaluation",
};

const THUMBNAIL_BASE = "https://arcprize.org/media/images/thumbnails";

const state = {
  activeDataset: "arc1Training",
  query: "",
};

const rows = document.querySelector("#task-rows");
const title = document.querySelector("#dataset-title");
const count = document.querySelector("#dataset-count");
const search = document.querySelector("#task-search");
const rowTemplate = document.querySelector("#task-row-template");

function thumbnailUrl(taskId, size) {
  return `${THUMBNAIL_BASE}/${taskId}-${size}.jpg`;
}

function taskUrl(taskId) {
  return `https://arcprize.org/tasks/${taskId}`;
}

function visibleTaskIds() {
  const taskIds = window.ARC_TASKS[state.activeDataset] || [];
  const query = state.query.trim().toLowerCase();
  if (!query) {
    return taskIds;
  }

  return taskIds.filter((taskId) => taskId.includes(query));
}

function updateTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    const isActive = tab.dataset.tab === state.activeDataset;
    tab.classList.toggle("is-active", isActive);
    tab.setAttribute("aria-current", isActive ? "page" : "false");
  });
}

function renderRows(taskIds) {
  rows.replaceChildren();

  if (taskIds.length === 0) {
    const row = document.createElement("tr");
    row.className = "empty-row";
    row.innerHTML = '<td colspan="3">No tasks match this search.</td>';
    rows.append(row);
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const taskId of taskIds) {
    const row = rowTemplate.content.firstElementChild.cloneNode(true);
    const link = row.querySelector(".task-link");
    const large = row.querySelector(".thumbnail-large");
    const small = row.querySelector(".thumbnail-small");

    link.href = taskUrl(taskId);
    link.textContent = taskId;
    large.src = thumbnailUrl(taskId, "large");
    large.alt = `${taskId} training samples`;
    small.src = thumbnailUrl(taskId, "small");
    small.alt = `${taskId} test sample`;

    fragment.append(row);
  }

  rows.append(fragment);
}

function render() {
  const allTaskIds = window.ARC_TASKS[state.activeDataset] || [];
  const taskIds = visibleTaskIds();
  const datasetName = DATASETS[state.activeDataset];

  document.title = `${datasetName} - ARC-AGI Tasks Viewer`;
  title.textContent = datasetName;
  count.textContent = state.query
    ? `${taskIds.length} of ${allTaskIds.length} tasks`
    : `${allTaskIds.length} tasks`;

  updateTabs();
  renderRows(taskIds);
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    state.activeDataset = tab.dataset.tab;
    state.query = "";
    search.value = "";
    render();
  });
});

search.addEventListener("input", () => {
  state.query = search.value;
  render();
});

render();
