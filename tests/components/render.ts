import { experimental_AstroContainer as AstroContainer } from 'astro/container';

export async function render(component: any, props: Record<string, unknown>): Promise<string> {
  const container = await AstroContainer.create();
  return container.renderToString(component, { props });
}
