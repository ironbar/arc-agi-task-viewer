const DATASETS = {
  arc1Training: { name: "ARC-AGI-1 training", directory: "arc1-training" },
  arc1Evaluation: { name: "ARC-AGI-1 evaluation", directory: "arc1-evaluation" },
  arc2Training: { name: "ARC-AGI-2 training", directory: "arc2-training" },
  arc2Evaluation: { name: "ARC-AGI-2 evaluation", directory: "arc2-evaluation" },
};

const PAGE_SIZE = 48;
const state = { activeDataset: "arc1Training", query: "", rendered: 0 };

const gallery = document.querySelector("#task-gallery");
const cardTemplate = document.querySelector("#task-card-template");
const datasetTitle = document.querySelector("#dataset-title");
const datasetCount = document.querySelector("#dataset-count");
const search = document.querySelector("#task-search");
const emptyState = document.querySelector("#empty-state");
const sentinel = document.querySelector("#load-sentinel");
const viewer = document.querySelector("#image-viewer");
const viewerImage = document.querySelector("#viewer-image");
const viewerTitle = document.querySelector("#viewer-title");
const viewerClose = document.querySelector("#viewer-close");

function visibleTaskIds() {
  const taskIds = window.ARC_TASKS[state.activeDataset] || [];
  const query = state.query.trim().toLowerCase();
  return query ? taskIds.filter((taskId) => taskId.includes(query)) : taskIds;
}

function thumbnailUrl(taskId) {
  return `thumbnails/${DATASETS[state.activeDataset].directory}/${taskId}.png`;
}

function taskUrl(taskId) {
  return `https://arcprize.org/tasks/${taskId}`;
}

function updateHeading(taskIds) {
  const dataset = DATASETS[state.activeDataset];
  const allCount = (window.ARC_TASKS[state.activeDataset] || []).length;
  datasetTitle.textContent = dataset.name;
  datasetCount.textContent = state.query ? `${taskIds.length} of ${allCount} tasks` : `${allCount.toLocaleString()} tasks`;
  document.title = `${dataset.name} - ARC-AGI Task Gallery`;
}

function createCard(taskId) {
  const card = cardTemplate.content.firstElementChild.cloneNode(true);
  const link = card.querySelector(".task-link");
  const button = card.querySelector(".thumbnail-button");
  const image = card.querySelector("img");
  const description = `${taskId}: all training and test input-output examples`;

  link.href = taskUrl(taskId);
  link.textContent = taskId;
  image.src = thumbnailUrl(taskId);
  image.alt = description;
  button.dataset.taskId = taskId;
  button.setAttribute("aria-label", `Expand ${description}`);
  return card;
}

function renderMore() {
  const taskIds = visibleTaskIds();
  const nextTaskIds = taskIds.slice(state.rendered, state.rendered + PAGE_SIZE);
  if (!nextTaskIds.length) return;
  const fragment = document.createDocumentFragment();
  nextTaskIds.forEach((taskId) => fragment.append(createCard(taskId)));
  gallery.append(fragment);
  state.rendered += nextTaskIds.length;
}

function resetGallery() {
  const taskIds = visibleTaskIds();
  state.rendered = 0;
  gallery.replaceChildren();
  emptyState.hidden = taskIds.length !== 0;
  sentinel.hidden = taskIds.length === 0;
  updateHeading(taskIds);
  renderMore();
}

function selectDataset(datasetKey) {
  state.activeDataset = datasetKey;
  state.query = "";
  search.value = "";
  document.querySelectorAll(".dataset-tab").forEach((tab) => {
    const isActive = tab.dataset.dataset === datasetKey;
    tab.classList.toggle("is-active", isActive);
    tab.setAttribute("aria-current", isActive ? "page" : "false");
  });
  resetGallery();
}

function openViewer(taskId, image) {
  viewerTitle.textContent = taskId;
  viewerImage.src = image.src;
  viewerImage.alt = image.alt;
  viewer.showModal();
}

function closeViewer() {
  viewer.close();
  viewerImage.removeAttribute("src");
  viewerImage.alt = "";
}

document.querySelectorAll(".dataset-tab").forEach((tab) => {
  tab.addEventListener("click", () => selectDataset(tab.dataset.dataset));
});

search.addEventListener("input", () => {
  state.query = search.value;
  resetGallery();
});

gallery.addEventListener("click", (event) => {
  const button = event.target.closest(".thumbnail-button");
  if (button) openViewer(button.dataset.taskId, button.querySelector("img"));
});

viewerClose.addEventListener("click", closeViewer);
viewer.addEventListener("click", (event) => {
  if (event.target === viewer) closeViewer();
});

new IntersectionObserver((entries) => {
  if (entries.some((entry) => entry.isIntersecting)) renderMore();
}, { rootMargin: "600px" }).observe(sentinel);

selectDataset(state.activeDataset);
