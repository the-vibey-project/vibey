// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { ShareComposer } from '../../src/core/share';

const composer = new ShareComposer();

describe('ShareComposer', () => {
  it('says the project name, phase and cycle in one sentence', () => {
    expect(composer.compose({ name: 'Greeter', phase: 'BUILD', cycle: 'Cycle 2 of 5' })).toEqual({
      title: 'Greeter on krypton',
      message: 'Greeter is in BUILD, cycle 2 of 5.',
    });
  });

  it('leaves the cycle out when there is none', () => {
    expect(composer.compose({ name: 'Greeter', phase: 'DONE', cycle: '' }).message).toBe('Greeter is in DONE.');
  });

  it('never sends anything but the three fields, whatever else is on the object', () => {
    const card = {
      name: 'Greeter',
      phase: 'BUILD',
      cycle: '',
      id: 'p-secret-id',
      openGates: 3,
      token: 'host-token',
      path: '/home/me/projects/greeter',
      cost: '$41.20',
    };
    const text = composer.compose(card);
    const everything = JSON.stringify(text);
    for (const leaked of ['p-secret-id', 'host-token', '/home/me', '$41.20', '3']) expect(everything).not.toContain(leaked);
  });

  it('trims what it is given and caps a name that is longer than the hub allows', () => {
    const long = 'a'.repeat(100);
    expect(composer.compose({ name: `  ${long}  `, phase: ' BUILD ', cycle: ' ' }).title).toBe(`${'a'.repeat(ShareComposer.NAME_LIMIT)} on krypton`);
    expect(composer.compose({ name: ' x ', phase: ' BUILD ', cycle: ' ' }).message).toBe('x is in BUILD.');
  });
});
