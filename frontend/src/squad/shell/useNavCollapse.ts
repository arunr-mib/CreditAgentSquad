import { useEffect, useState } from 'react';

const NAV_KEY = 'squad.nav.collapsed';
const WIDE = 1280;
const ROOMY = 960; // names beside the icons from here up, unless the person folded them away

function storedCollapsed(): boolean {
  try {
    const kept = localStorage.getItem(NAV_KEY); // the person's own choice wins; with none, open wherever there is room
    return kept === null ? window.innerWidth < ROOMY : kept === 'true';
  } catch {
    return window.innerWidth < ROOMY;
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
