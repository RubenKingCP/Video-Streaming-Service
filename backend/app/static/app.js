// app.js
// Logic of the demo page: loads the video list, plays the selected video with hls.js
// and logs every downloaded segment together with the instance (Pod) that served it.
// Loaded by index.html AFTER hls.js, so the global "Hls" object already exists.

// Get references to the page elements we need
const select = document.getElementById("video-select");
const playBtn = document.getElementById("play-btn");
const statusEl = document.getElementById("status");
const video = document.getElementById("player");
const logEl = document.getElementById("log");

// The current hls.js instance (null when nothing is playing)
let hls = null;

// Adds a line to the segment log and scrolls to the bottom
function log(line) {
  // textContent (not innerHTML) so no text can be interpreted as HTML
  logEl.textContent += line + "\n";
  // Keep the newest line visible
  logEl.scrollTop = logEl.scrollHeight;
}

// Loads the list of videos from the backend and fills the dropdown
async function loadVideos() {
  try {
    // Call our endpoint GET /videos
    const response = await fetch("/videos");
    // Turn the JSON response into a JavaScript object
    const data = await response.json();
    // Remove any old options
    select.innerHTML = "";
    // Add one <option> per video
    for (const v of data.videos) {
      // Create the option element
      const option = document.createElement("option");
      // The value is the playlist URL, e.g. /videos/sample/index.m3u8
      option.value = v.playlist;
      // The visible text is the video id
      option.textContent = v.id;
      // Add it to the dropdown
      select.appendChild(option);
    }
    // Show how many videos were found and which instance answered
    statusEl.textContent = `${data.videos.length} video(s) found. List served by: ${data.instance}`;
    // Disable the button if there is nothing to play
    playBtn.disabled = data.videos.length === 0;
  } catch (err) {
    // Network error or invalid JSON
    statusEl.textContent = "Could not load the video list: " + err;
  }
}

// Starts playing the given playlist URL
function play(playlistUrl) {
  // Clear the log for the new video
  logEl.textContent = "";
  // If a previous video is playing, stop it and free its resources
  if (hls) {
    hls.destroy();
    hls = null;
  }

  // Case 1: the browser needs hls.js (Chrome, Firefox, Edge)
  if (Hls.isSupported()) {
    // Create a new hls.js player
    hls = new Hls();
    // Load the playlist; hls.js will then request the segments by itself
    hls.loadSource(playlistUrl);
    // Connect hls.js to the <video> element
    hls.attachMedia(video);

    // Fired every time a segment has been downloaded
    hls.on(Hls.Events.FRAG_LOADED, (event, data) => {
      // The XMLHttpRequest used for the download, so we can read the response headers
      const xhr = data.networkDetails;
      // Our backend's X-Served-By header: the name of the instance (Pod) that served this segment
      const servedBy = xhr && xhr.getResponseHeader ? xhr.getResponseHeader("X-Served-By") : "?";
      // Segment size in kilobytes
      const kb = (data.frag.stats.loaded / 1024).toFixed(0);
      // Download time in milliseconds
      const ms = (data.frag.stats.loading.end - data.frag.stats.loading.start).toFixed(0);
      // Write one line: segment number, size, time, instance
      log(`segment #${data.frag.sn}  ${kb} KB  ${ms} ms  served by: ${servedBy}`);
    });

    // Fired on errors (e.g. 404 for a segment)
    hls.on(Hls.Events.ERROR, (event, data) => {
      // Only fatal errors stop playback, the others are retried automatically
      if (data.fatal) {
        statusEl.textContent = "Playback error: " + data.details;
      }
    });

  // Case 2: the browser plays HLS natively (Safari)
  } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
    // Just give the playlist URL to the <video> element
    video.src = playlistUrl;
    // No per-segment events here, so the log stays empty
    log("Native HLS playback (no per-segment log in this browser).");

  // Case 3: no HLS support at all
  } else {
    statusEl.textContent = "This browser cannot play HLS.";
    return;
  }

  // Start playback (muted, so the browser allows it without a click on the video)
  video.play().catch(() => {});
}

// When the button is clicked, play the selected video
playBtn.addEventListener("click", () => play(select.value));

// Load the video list as soon as the page opens
loadVideos();