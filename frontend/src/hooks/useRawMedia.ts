import { useState, useEffect, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';
import { sanitizeError } from '@/utils/sanitizeError';

export interface MediaFolder {
  id: string;
  displayName: string;
  fileCount: number;
}

export interface MediaFile {
  name: string;
  url: string;
  path: string;
  createdAt: string;
}

interface FolderMap {
  [folderId: string]: string;
}

const STORAGE_LIMIT_MB = 500;

function generateFolderId(): string {
  return `f${Date.now()}${Math.random().toString(36).slice(2, 6)}`;
}

export function useRawMedia() {
  const { user } = useAuth();
  const [folders, setFolders] = useState<MediaFolder[]>([]);
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentFolder, setCurrentFolder] = useState<string | null>(null);
  const [currentFolderName, setCurrentFolderName] = useState<string | null>(null);
  const [storageUsedMB, setStorageUsedMB] = useState(0);
  const [storageLimitMB] = useState(STORAGE_LIMIT_MB);
  const folderMapCache = useRef<FolderMap | null>(null);
  const hasFetched = useRef(false);

  const getFolderMap = useCallback(async (): Promise<FolderMap> => {
    if (folderMapCache.current) return folderMapCache.current;
    if (!user) return {};
    try {
      const { data, error } = await supabase.storage
        .from('raw-media')
        .download(`${user.id}/.folders.json`);
      if (data && !error) {
        const text = await data.text();
        const map = JSON.parse(text) as FolderMap;
        folderMapCache.current = map;
        return map;
      }
    } catch {}
    folderMapCache.current = {};
    return {};
  }, [user]);

  const saveFolderMap = useCallback(async (map: FolderMap) => {
    if (!user) return;
    folderMapCache.current = map;
    const blob = new Blob([JSON.stringify(map)], { type: 'application/json' });
    await supabase.storage
      .from('raw-media')
      .upload(`${user.id}/.folders.json`, blob, { upsert: true });
  }, [user]);

  const fetchFolders = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const { data, error } = await supabase.storage
        .from('raw-media')
        .list(user.id, { limit: 100, sortBy: { column: 'name', order: 'asc' } });

      if (error) throw error;

      const folderMap = await getFolderMap();
      const folderItems = (data || []).filter(
        item => item.id === null && item.name.startsWith('f')
      );
      const folderList: MediaFolder[] = [];
      let totalSize = 0;

      for (const folder of folderItems) {
        if (!folderMap[folder.name]) continue;

        const { data: filesInFolder } = await supabase.storage
          .from('raw-media')
          .list(`${user.id}/${folder.name}`, { limit: 1000 });

        const realFiles = (filesInFolder || []).filter(f => f.id !== null && f.name !== '.keep');
        for (const f of realFiles) {
          totalSize += (f.metadata as any)?.size || 0;
        }

        folderList.push({
          id: folder.name,
          displayName: folderMap[folder.name],
          fileCount: realFiles.length,
        });
      }

      setStorageUsedMB(Math.round((totalSize / (1024 * 1024)) * 100) / 100);
      setFolders(folderList);
    } catch (err: any) {
      toast.error('שגיאה בטעינת תיקיות');
    } finally {
      setLoading(false);
    }
  }, [user, getFolderMap]);

  const fetchFiles = useCallback(async (folderId: string, displayName?: string) => {
    if (!user) return;
    setLoading(true);
    setCurrentFolder(folderId);
    if (displayName) setCurrentFolderName(displayName);
    try {
      const { data, error } = await supabase.storage
        .from('raw-media')
        .list(`${user.id}/${folderId}`, {
          limit: 1000,
          sortBy: { column: 'created_at', order: 'desc' },
        });

      if (error) throw error;

      const fileItems = (data || []).filter(item => item.id !== null && item.name !== '.keep');
      const mapped: MediaFile[] = fileItems.map(f => {
        const path = `${user.id}/${folderId}/${f.name}`;
        const { data: urlData } = supabase.storage.from('raw-media').getPublicUrl(path);
        return {
          name: f.name,
          url: urlData.publicUrl,
          path,
          createdAt: f.created_at || '',
        };
      });

      setFiles(mapped);
    } catch (err: any) {
      toast.error('שגיאה בטעינת קבצים');
    } finally {
      setLoading(false);
    }
  }, [user]);

  const createFolder = useCallback(async (displayName: string) => {
    if (!user) return;
    try {
      const folderId = generateFolderId();
      const placeholder = new Blob([''], { type: 'text/plain' });
      const { error } = await supabase.storage
        .from('raw-media')
        .upload(`${user.id}/${folderId}/.keep`, placeholder);

      if (error) throw error;

      const map = await getFolderMap();
      map[folderId] = displayName;
      await saveFolderMap(map);

      toast.success('התיקייה נוצרה');
      await fetchFolders();
    } catch (err: any) {
      toast.error(sanitizeError(err));
    }
  }, [user, fetchFolders, getFolderMap, saveFolderMap]);

  const renameFolder = useCallback(async (folderId: string, newName: string) => {
    if (!user) return;
    try {
      const map = await getFolderMap();
      map[folderId] = newName;
      await saveFolderMap(map);
      setCurrentFolderName(newName);
      toast.success('שם התיקייה עודכן');
      await fetchFolders();
    } catch (err: any) {
      toast.error('שגיאה בעדכון שם התיקייה');
    }
  }, [user, getFolderMap, saveFolderMap, fetchFolders]);

  const deleteFolder = useCallback(async (folderId: string) => {
    if (!user) return;
    try {
      const { data: filesInFolder } = await supabase.storage
        .from('raw-media')
        .list(`${user.id}/${folderId}`, { limit: 1000 });

      if (filesInFolder && filesInFolder.length > 0) {
        const paths = filesInFolder.map(f => `${user.id}/${folderId}/${f.name}`);
        await supabase.storage.from('raw-media').remove(paths);
      }

      const map = await getFolderMap();
      delete map[folderId];
      await saveFolderMap(map);

      toast.success('התיקייה נמחקה');
      setCurrentFolder(null);
      setCurrentFolderName(null);
      await fetchFolders();
    } catch (err: any) {
      toast.error('שגיאה במחיקת תיקייה');
    }
  }, [user, getFolderMap, saveFolderMap, fetchFolders]);

  const uploadFiles = useCallback(async (folderId: string, fileList: File[]) => {
    if (!user) return;
    setLoading(true);
    try {
      for (const file of fileList) {
        const ext = file.name.split('.').pop();
        const fileName = `${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`;
        const path = `${user.id}/${folderId}/${fileName}`;

        const { error } = await supabase.storage
          .from('raw-media')
          .upload(path, file);

        if (error) throw error;
      }
      toast.success(`${fileList.length} קבצים הועלו בהצלחה`);
      await fetchFiles(folderId);
      await fetchFolders();
    } catch (err: any) {
      toast.error(sanitizeError(err));
    } finally {
      setLoading(false);
    }
  }, [user, fetchFiles, fetchFolders]);

  const deleteFile = useCallback(async (path: string) => {
    try {
      const { error } = await supabase.storage.from('raw-media').remove([path]);
      if (error) throw error;
      toast.success('הקובץ נמחק');
      if (currentFolder) await fetchFiles(currentFolder);
      await fetchFolders();
    } catch (err: any) {
      toast.error('שגיאה במחיקת קובץ');
    }
  }, [currentFolder, fetchFiles, fetchFolders]);

  useEffect(() => {
    if (!hasFetched.current && user) {
      hasFetched.current = true;
      fetchFolders();
    }
  }, [user, fetchFolders]);

  return {
    folders, files, loading, currentFolder, currentFolderName,
    storageUsedMB, storageLimitMB,
    setCurrentFolder, setCurrentFolderName,
    fetchFolders, fetchFiles, createFolder, renameFolder, deleteFolder, uploadFiles, deleteFile,
  };
}
