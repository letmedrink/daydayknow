import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

interface PreviewState {
  /** 当前预览/浏览的页面路径（WikiTree、WikiBrowser、PreviewPanel 三者共享） */
  activePath: string | null;
  /** 右侧预览面板是否打开 */
  previewOpen: boolean;
  /** 打开预览面板并导航到指定页面 */
  openPreview: (path: string) => void;
  /** 关闭预览面板 */
  closePreview: () => void;
  /** 仅设置活动路径（不自动打开预览面板） */
  setActivePath: (path: string) => void;
}

const PreviewContext = createContext<PreviewState>({
  activePath: null,
  previewOpen: false,
  openPreview: () => {},
  closePreview: () => {},
  setActivePath: () => {},
});

export function PreviewProvider({ children }: { children: ReactNode }) {
  const [activePath, setActivePathState] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const openPreview = useCallback((path: string) => {
    setActivePathState(path);
    setPreviewOpen(true);
  }, []);

  const closePreview = useCallback(() => {
    setPreviewOpen(false);
  }, []);

  const setActivePath = useCallback((path: string) => {
    setActivePathState(path);
  }, []);

  return (
    <PreviewContext.Provider value={{ activePath, previewOpen, openPreview, closePreview, setActivePath }}>
      {children}
    </PreviewContext.Provider>
  );
}

export function usePreview() {
  return useContext(PreviewContext);
}
