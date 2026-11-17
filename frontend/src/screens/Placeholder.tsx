import { Link } from '@tanstack/react-router';
import { Hammer } from 'lucide-react';
import { Button, Card, EmptyState, PageHeader } from '@/design';

export function Placeholder({ title, description }: { title: string; description: string }) {
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Bank of Stoic · Commercial lending" title={title} />
      <Card>
        <EmptyState
          icon={<Hammer size={20} strokeWidth={1.75} aria-hidden />}
          title={`${title} is not built yet`}
          description={`${description}. It arrives in a later milestone; the command centre, the covenant workspace and the spread grid show the system it will be built from.`}
          action={
            <Button asChild variant="secondary">
              <Link to="/showcase/command-centre">Go to the command centre</Link>
            </Button>
          }
        />
      </Card>
    </div>
  );
}
