import { useState, useRef } from 'react';
import AppLayout from '@/components/AppLayout';
import { useRawMedia } from '@/hooks/useRawMedia';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  FolderPlus,
  Upload,
  ArrowRight,
  Trash2,
  Film,
  Folder,
  Loader2,
  MoreVertical,
  Pencil,
  HardDrive,
} from 'lucide-react';

export default function MediaPage() {
  const { t } = useLanguage();
  const {
    folders,
    files,
    loading,
    currentFolder,
    currentFolderName,
    storageUsedMB,
    storageLimitMB,
    fetchFiles,
    createFolder,
    renameFolder,
    deleteFolder,
    uploadFiles,
    deleteFile,
    setCurrentFolder,
    setCurrentFolderName,
    fetchFolders,
  } = useRawMedia();

  const [newFolderOpen, setNewFolderOpen] = useState(false);
  const [folderName, setFolderName] = useState('');
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameFolderId, setRenameFolderId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteFolderId, setDeleteFolderId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);

  const handleCreateFolder = async () => {
    if (!folderName.trim()) return;
    await createFolder(folderName.trim());
    setFolderName('');
    setNewFolderOpen(false);
  };

  const handleRename = async () => {
    if (!renameValue.trim() || !renameFolderId) return;
    await renameFolder(renameFolderId, renameValue.trim());
    setRenameOpen(false);
    setRenameFolderId(null);
    setRenameValue('');
  };

  const handleDeleteFolder = async () => {
    if (!deleteFolderId) return;
    await deleteFolder(deleteFolderId);
    setDeleteConfirmOpen(false);
    setDeleteFolderId(null);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !currentFolder) return;
    const fileList = Array.from(e.target.files);
    await uploadFiles(currentFolder, fileList);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const goBack = () => {
    setCurrentFolder(null);
    setCurrentFolderName(null);
    fetchFolders();
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.types.includes('Files')) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    dragCounter.current = 0;
    if (!currentFolder || !e.dataTransfer.files.length) return;
    const fileList = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('video/'));
    if (fileList.length === 0) {
      const { toast } = await import('sonner');
      toast.error(t('mediaLib.onlyVideoFiles'));
      return;
    }
    await uploadFiles(currentFolder, fileList);
  };

  const storagePercent = storageLimitMB > 0 ? Math.min((storageUsedMB / storageLimitMB) * 100, 100) : 0;

  return (
    <AppLayout title={t('mediaLib.title')}>
      <div className="max-w-6xl mx-auto flex gap-6">
        {/* Main content */}
        <div className="flex-1 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {currentFolder && (
                <Button variant="ghost" size="icon" onClick={goBack}>
                  <ArrowRight className="h-5 w-5" />
                </Button>
              )}
              <h1 className="text-2xl font-bold text-foreground">
                {currentFolderName || currentFolder || t('mediaLib.title')}
              </h1>
            </div>
            <div className="flex gap-2">
              {currentFolder ? (
                <>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="video/*"
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                  <Button
                    onClick={() => fileInputRef.current?.click()}
                    className="gradient-primary text-primary-foreground gap-2 rounded-xl"
                    disabled={loading}
                  >
                    <Upload className="h-4 w-4" />
                    {t('mediaLib.uploadVideos')}
                  </Button>
                </>
              ) : (
                <Button
                  onClick={() => setNewFolderOpen(true)}
                  className="gradient-primary text-primary-foreground gap-2 rounded-xl"
                >
                  <FolderPlus className="h-4 w-4" />
                  {t('mediaLib.newFolder')}
                </Button>
              )}
            </div>
          </div>

          {loading && (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}

          {/* Folder grid */}
          {!loading && !currentFolder && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {folders.map(folder => (
                <Card
                  key={folder.id}
                  className="cursor-pointer hover:shadow-md transition-shadow glass group relative"
                  onClick={() => fetchFiles(folder.id, folder.displayName)}
                >
                  {/* Folder context menu */}
                  <div
                    className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity z-10"
                    onClick={e => e.stopPropagation()}
                  >
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start">
                        <DropdownMenuItem
                          onClick={() => {
                            setRenameFolderId(folder.id);
                            setRenameValue(folder.displayName);
                            setRenameOpen(true);
                          }}
                        >
                          <Pencil className="h-4 w-4 ml-2" />
                          {t('mediaLib.rename')}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => {
                            setDeleteFolderId(folder.id);
                            setDeleteConfirmOpen(true);
                          }}
                        >
                          <Trash2 className="h-4 w-4 ml-2" />
                          {t('mediaLib.deleteFolder')}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <CardContent className="p-6 flex flex-col items-center gap-3 text-center">
                    <Folder className="h-12 w-12 text-primary" />
                    <span className="font-medium text-foreground truncate w-full">
                      {folder.displayName}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {folder.fileCount} {t('mediaLib.files')}
                    </span>
                  </CardContent>
                </Card>
              ))}
              {folders.length === 0 && (
                <div className="col-span-full text-center py-16 text-muted-foreground">
                  <Folder className="h-16 w-16 mx-auto mb-4 opacity-30" />
                  <p>{t('mediaLib.noFolders')}</p>
                </div>
              )}
            </div>
          )}

          {/* Files grid with drag & drop */}
          {!loading && currentFolder && (
            <div
              className="relative"
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              {isDragging && (
                <div className="absolute inset-0 z-20 flex items-center justify-center rounded-xl border-2 border-dashed border-primary bg-primary/5 backdrop-blur-sm">
                  <div className="text-center">
                    <Upload className="h-12 w-12 mx-auto mb-3 text-primary animate-bounce" />
                    <p className="text-lg font-semibold text-primary">{t('mediaLib.releaseToUpload')}</p>
                    <p className="text-sm text-muted-foreground">{t('mediaLib.videoFilesOnly')}</p>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {files.map(file => (
                <Card key={file.path} className="overflow-hidden glass group">
                  <div className="relative aspect-video bg-muted">
                    <video
                      src={file.url}
                      className="w-full h-full object-cover"
                      muted
                      preload="metadata"
                      onMouseEnter={e => (e.target as HTMLVideoElement).play()}
                      onMouseLeave={e => {
                        const v = e.target as HTMLVideoElement;
                        v.pause();
                        v.currentTime = 0;
                      }}
                    />
                    <Button
                      variant="destructive"
                      size="icon"
                      className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8"
                      onClick={() => deleteFile(file.path)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2">
                      <Film className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-sm text-foreground truncate">{file.name}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {files.length === 0 && (
                <div className="col-span-full text-center py-16 text-muted-foreground">
                  <Upload className="h-16 w-16 mx-auto mb-4 opacity-30" />
                  <p>{t('mediaLib.dragOrClick')}</p>
                </div>
              )}
              </div>
            </div>
          )}
        </div>

        {/* Storage sidebar */}
        <div className="hidden md:block w-56 shrink-0">
          <Card className="glass sticky top-24">
            <CardContent className="p-5 space-y-4">
              <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
                <HardDrive className="h-4 w-4 text-primary" />
                <span>{t('mediaLib.storage')}</span>
              </div>
              <Progress value={storagePercent} className="h-2" />
              <div className="text-xs text-muted-foreground text-center">
                {storageUsedMB < 1
                  ? `${Math.round(storageUsedMB * 1024)} KB`
                  : `${storageUsedMB.toFixed(1)} MB`}
                {' '}{t('mediaLib.of')} {storageLimitMB >= 1000 ? `${(storageLimitMB / 1000).toFixed(0)} GB` : `${storageLimitMB} MB`}
              </div>
              {storagePercent >= 80 && (
                <p className="text-xs text-destructive text-center">
                  {storagePercent >= 100
                    ? t('mediaLib.storageFull')
                    : t('mediaLib.storageAlmostFull')}
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* New Folder Dialog */}
      <Dialog open={newFolderOpen} onOpenChange={setNewFolderOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('mediaLib.newFolderTitle')}</DialogTitle>
            <DialogDescription>{t('mediaLib.newFolderDesc')}</DialogDescription>
          </DialogHeader>
          <Input
            value={folderName}
            onChange={e => setFolderName(e.target.value)}
            placeholder={t('mediaLib.folderName')}
            onKeyDown={e => e.key === 'Enter' && handleCreateFolder()}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewFolderOpen(false)}>
              {t('mediaLib.cancel')}
            </Button>
            <Button onClick={handleCreateFolder} disabled={!folderName.trim()}>
              {t('mediaLib.createFolder')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rename Dialog */}
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('mediaLib.renameFolderTitle')}</DialogTitle>
            <DialogDescription>{t('mediaLib.renameFolderDesc')}</DialogDescription>
          </DialogHeader>
          <Input
            value={renameValue}
            onChange={e => setRenameValue(e.target.value)}
            placeholder={t('mediaLib.newName')}
            onKeyDown={e => e.key === 'Enter' && handleRename()}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameOpen(false)}>
              {t('mediaLib.cancel')}
            </Button>
            <Button onClick={handleRename} disabled={!renameValue.trim()}>
              {t('mediaLib.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Folder Confirmation */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('mediaLib.deleteFolderTitle')}</DialogTitle>
            <DialogDescription>
              {t('mediaLib.deleteFolderConfirm')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)}>
              {t('mediaLib.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDeleteFolder}>
              {t('mediaLib.deleteFolderBtn')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
