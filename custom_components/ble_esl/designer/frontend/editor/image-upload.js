import { t } from "../i18n.js";
import { jpegOrientation } from "../model.js";

// Image uploads are asynchronous and can outlive the element or editor session
// they started from. Keep the upload lifecycle together and guard every commit.
export function handleImageUpload(panel, input) {
  const file = input.files[0];
  if (!file) return;
  const id = panel.element.id,
    sequence = (panel.uploadSequence = (panel.uploadSequence || 0) + 1),
    ownerTag = panel.tag,
    ownerDocument = panel.document,
    ownerSession = panel._automationSessionToken;
  const reader = new FileReader();
  const upload = new Promise((resolve, reject) => {
    reader.onload = async () => {
      try {
        let image = reader.result;
        // The renderer ignores a photo's EXIF orientation, which the browser
        // applies: a portrait phone photo would print turned 90°. A photo that
        // carries one is redrawn (and as a tag is small, capped in size) so
        // the orientation is in its pixels. The rest is kept byte for byte.
        try {
          const head = new Uint8Array(await file.slice(0, 65536).arrayBuffer());
          if (jpegOrientation(head) > 1) {
            const bitmap = await createImageBitmap(file, {
              imageOrientation: "from-image",
            });
            const scale = Math.min(
                1,
                2048 / Math.max(bitmap.width, bitmap.height),
              ),
              canvas = document.createElement("canvas");
            canvas.width = Math.max(1, Math.round(bitmap.width * scale));
            canvas.height = Math.max(1, Math.round(bitmap.height * scale));
            canvas
              .getContext("2d")
              .drawImage(bitmap, 0, 0, canvas.width, canvas.height);
            bitmap.close();
            const redrawn = canvas.toDataURL("image/jpeg", 0.92);
            // A canvas the browser refuses gives "data:," rather than an error.
            if (redrawn.length > 100) image = redrawn;
          }
        } catch {
          // Keep the file as it is when the browser cannot decode it.
        }
        const element = ownerDocument.elements.find((item) => item.id === id);
        if (
          !element ||
          sequence !== panel.uploadSequence ||
          panel.document !== ownerDocument ||
          panel.tag !== ownerTag ||
          panel._automationSessionToken !== ownerSession
        ) {
          resolve();
          return;
        }
        panel.checkpoint();
        element.image = image;
        if (!panel.error) panel.status = "Image added";
        panel.edited();
        resolve();
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = () =>
      reject(reader.error || new Error(t(panel.hass, "Image upload failed")));
    reader.readAsDataURL(file);
  });
  panel.pendingUploads.add(upload);
  panel.busy = true;
  panel.error = false;
  panel.errorSource = null;
  panel.status = "Loading image…";
  panel.render();
  upload
    .catch((error) => {
      if (
        ownerSession === panel._automationSessionToken &&
        ownerDocument === panel.document
      )
        panel.report(error);
    })
    .finally(() => {
      panel.pendingUploads.delete(upload);
      if (ownerSession === panel._automationSessionToken) panel.busy = false;
      panel.render();
    });
}
