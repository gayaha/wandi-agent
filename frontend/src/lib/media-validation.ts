export interface ValidationResult {
  valid: boolean;
  error?: string;
  mediaType: 'image' | 'video';
}

const IMAGE_TYPES = ['image/jpeg', 'image/png'];
const VIDEO_TYPES = ['video/mp4', 'video/quicktime'];
const MAX_IMAGE_SIZE = 8 * 1024 * 1024;
const MAX_VIDEO_SIZE = 500 * 1024 * 1024;
const MIN_ASPECT_RATIO = 4 / 5;
const MAX_ASPECT_RATIO = 1.91;
const MAX_CAROUSEL_ITEMS = 10;
const MIN_CAROUSEL_ITEMS = 2;

export function validateMediaFile(file: File): ValidationResult {
  const isImage = IMAGE_TYPES.includes(file.type);
  const isVideo = VIDEO_TYPES.includes(file.type);

  if (!isImage && !isVideo) {
    return {
      valid: false,
      error: 'פורמט לא נתמך. השתמש ב-JPEG, PNG, MP4 או MOV',
      mediaType: 'image',
    };
  }

  const mediaType = isImage ? 'image' : 'video';

  if (isImage && file.size > MAX_IMAGE_SIZE) {
    return {
      valid: false,
      error: `התמונה גדולה מדי (${(file.size / 1024 / 1024).toFixed(1)}MB). מקסימום 8MB`,
      mediaType,
    };
  }

  if (isVideo && file.size > MAX_VIDEO_SIZE) {
    return {
      valid: false,
      error: `הסרטון גדול מדי (${(file.size / 1024 / 1024).toFixed(1)}MB). מקסימום 500MB`,
      mediaType,
    };
  }

  return { valid: true, mediaType };
}

export function validateImageDimensions(width: number, height: number): { valid: boolean; error?: string } {
  const ratio = width / height;
  if (ratio < MIN_ASPECT_RATIO || ratio > MAX_ASPECT_RATIO) {
    return {
      valid: false,
      error: `יחס גובה-רוחב לא תקין (${ratio.toFixed(2)}). נדרש בין 4:5 ל-1.91:1`,
    };
  }
  if (width < 320 || height < 320) {
    return {
      valid: false,
      error: 'התמונה קטנה מדי. מינימום 320x320 פיקסלים',
    };
  }
  return { valid: true };
}

export function validateCarouselFiles(files: File[]): { valid: boolean; error?: string } {
  if (files.length < MIN_CAROUSEL_ITEMS) {
    return { valid: false, error: `קרוסלה דורשת לפחות ${MIN_CAROUSEL_ITEMS} פריטים` };
  }
  if (files.length > MAX_CAROUSEL_ITEMS) {
    return { valid: false, error: `קרוסלה תומכת במקסימום ${MAX_CAROUSEL_ITEMS} פריטים` };
  }
  return { valid: true };
}
