// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Finds the controls a screen reader would meet and cannot name (#1698, slice A). */

export interface TreeNode {
  readonly type?: string;
  readonly props?: Record<string, unknown>;
  readonly children?: readonly (TreeNode | string)[] | null;
}

export interface Control {
  readonly kind: 'button' | 'link' | 'input' | 'switch' | 'pressable';
  readonly name: string;
  readonly role: string | undefined;
}

export class AccessibleControls {
  /** Every control in the tree: what it is, the name a screen reader would speak, its role. */
  find(root: TreeNode | readonly TreeNode[] | null): readonly Control[] {
    const found: Control[] = [];
    const roots = root === null ? [] : Array.isArray(root) ? (root as readonly TreeNode[]) : [root as TreeNode];
    for (const node of roots) this.walk(node, found);
    return found;
  }

  /** The controls with no name, or a pressable with no role (it would be announced as nothing). */
  flaws(root: TreeNode | readonly TreeNode[] | null): readonly string[] {
    return this.find(root).flatMap((control) => {
      const flaws: string[] = [];
      if (control.name.trim() === '') flaws.push(`a ${control.kind} with no accessible name`);
      if (control.kind === 'pressable') flaws.push(`a pressable named "${control.name}" with no accessibilityRole`);
      return flaws;
    });
  }

  private walk(node: TreeNode | string, found: Control[]): void {
    if (typeof node === 'string') return;
    const props = node.props ?? {};
    const control = this.classify(node, props);
    if (control !== undefined) found.push(control);
    for (const child of node.children ?? []) this.walk(child, found);
  }

  private classify(node: TreeNode, props: Record<string, unknown>): Control | undefined {
    const role = typeof props.accessibilityRole === 'string' ? props.accessibilityRole : undefined;
    const kind =
      node.type === 'TextInput' ? 'input'
      : node.type === 'RCTSwitch' ? 'switch'
      : props.accessible === true && typeof props.onClick === 'function' ? (role === 'link' ? 'link' : role === 'button' ? 'button' : 'pressable')
      : undefined;
    if (kind === undefined) return undefined;
    return { kind, name: this.name(node, props), role };
  }

  /** The label if there is one, otherwise the text inside, as a screen reader joins it. */
  private name(node: TreeNode, props: Record<string, unknown>): string {
    for (const key of ['accessibilityLabel', 'aria-label']) {
      const label = props[key];
      if (typeof label === 'string' && label !== '') return label;
    }
    return this.text(node).join(' ').trim();
  }

  private text(node: TreeNode | string): string[] {
    if (typeof node === 'string') return [node];
    return (node.children ?? []).flatMap((child) => this.text(child));
  }
}
