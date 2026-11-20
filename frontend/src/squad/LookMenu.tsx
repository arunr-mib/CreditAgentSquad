// frontend/src/squad/LookMenu.tsx
import { Palette } from 'lucide-react';
import { DropdownMenu } from 'radix-ui';
import { LOOK_IDS, LOOKS } from './looks';
import { useLook } from './useLook';

export function LookMenu() {
  const { look, setLook, root } = useLook();
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger className="sq-iconbtn" aria-label={`Look: ${LOOKS[look].label}`}>
        <Palette size={16} aria-hidden />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal container={root}>
        <DropdownMenu.Content className="sq-menu" align="end" sideOffset={6}>
          <DropdownMenu.RadioGroup value={look} onValueChange={(v) => setLook(v as (typeof LOOK_IDS)[number])}>
            {LOOK_IDS.map((id) => (
              <DropdownMenu.RadioItem key={id} value={id} className="sq-menuitem">
                <span className="sq-swatch" style={{ background: `linear-gradient(135deg, ${LOOKS[id].swatch[0]} 50%, ${LOOKS[id].swatch[1]} 50%)` }} aria-hidden />
                {LOOKS[id].label}
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
