import { useEffect, useState } from 'react';

const NAV_KEY = 'squad.nav.collapsed';
const WIDE = 1280;

function storedCollapsed(): boolean {
  try {
    return localStorage.getItem(NAV_KEY) !== 'false'; // collapsed unless the person opened it
  } catch {
    return true;
  }
}

/**
 * The nav's state. Below 1280 px an open evidence drawer folds the nav away so the conversation keeps its room;
 * pressing the toggle then expands it at once (until the drawer closes) and the stored choice is left alone.
 */
export function useNavCollapse(evidenceOpen: boolean): { collapsed: boolean; toggle: () => void } {
  const [stored, setStored] = useState(storedCollapsed);
  const [wide, setWide] = useState(() => window.innerWidth >= WIDE);
  const [peek, setPeek] = useState(false);
  useEffect(() => {
    const onResize = () => setWide(window.innerWidth >= WIDE);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  if (!evidenceOpen && peek) setPeek(false); // the override lasts only as long as the drawer stays open
  const forced = evidenceOpen && !wide;
  const collapsed = forced ? !peek : stored;
  const toggle = () => {
    if (forced) {
      setPeek(!peek);
      return;
    }
    setStored((c) => {
      try {
        localStorage.setItem(NAV_KEY, String(!c));
      } catch {
        /* not remembered */
      }
      return !c;
    });
  };
  return { collapsed, toggle };
}
