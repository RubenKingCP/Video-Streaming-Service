import time
from locust import HttpUser, task, between

class VideoStreamingUser(HttpUser):
    # Περιμένει 1-2 δευτερόλεπτα πριν ξεκινήσει (σαν να περιηγείται στη σελίδα)
    wait_time = between(1, 2)

    @task
    def watch_video(self):
        # 1. Ζητάει τη λίστα με τα διαθέσιμα βίντεο
        response = self.client.get("/videos", name="/videos")
        if response.status_code != 200:
            return
            
        data = response.json()
        videos = data.get("videos", [])
        if not videos:
            return
            
        # Επιλέγουμε το πρώτο διαθέσιμο βίντεο από τη λίστα
        video = videos[0]
        video_id = video["id"]
        playlist_url = video["playlist"]

        # 2. Κατεβάζει το αρχείο playlist (.m3u8)
        playlist_response = self.client.get(playlist_url, name="/videos/{id}/index.m3u8")
        if playlist_response.status_code != 200:
            return

        # 3. Αναλύει το .m3u8 για να βρει τα ονόματα των αρχείων .ts
        segments = []
        for line in playlist_response.text.splitlines():
            line = line.strip()
            # Απομονώνει τις γραμμές που δεν είναι σχόλια/metadata (δεν ξεκινάνε με #)
            if line and not line.startswith('#'):
                segments.append(line)

        # 4. Προσομοίωση αναπαραγωγής HLS: Κατεβάζει τα segments ένα-ένα
        for segment in segments:
            segment_url = f"/videos/{video_id}/{segment}"
            self.client.get(segment_url, name="/videos/{id}/seg_NNN.ts")
            
            # Το αρχείο prepare_media.py φτιάχνει segments των 4 δευτερολέπτων από προεπιλογή
            # Ο client "περιμένει" 4 δευτερόλεπτα (αναπαραγωγή) πριν ζητήσει το επόμενο κομμάτι.
            time.sleep(4)