// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Runs programs with an argument vector, never through a shell.
 *
 * Nothing here interpolates a string into a command line: every caller passes argv, so a
 * task title, a branch name or a model's text can never become shell syntax. Declared by
 * `interfaces/process-runner-interface.ts`.
 */
import { spawn as nodeSpawn } from 'node:child_process';
import type {
  ChildHandle,
  CompletedProcess,
  ProcessExit,
  ProcessRunnerInterface,
  RunOptions,
} from './interfaces/process-runner-interface';

export class NodeProcessRunner implements ProcessRunnerInterface {
  run(command: string, args: readonly string[], options: RunOptions = {}): Promise<CompletedProcess> {
    const child = this.spawn(command, args, options);
    let stdout = '';
    let stderr = '';
    child.onStdout((text) => {
      stdout += text;
    });
    child.onStderr((text) => {
      stderr += text;
    });
    let timedOut = false;
    const timer =
      options.timeoutMs === undefined
        ? undefined
        : setTimeout(() => {
            timedOut = true;
            child.kill('SIGTERM');
          }, options.timeoutMs);
    return child.exited.then((exit) => {
      if (timer !== undefined) {
        clearTimeout(timer);
      }
      const error = timedOut ? `timed out after ${options.timeoutMs} ms` : exit.error;
      return {
        code: exit.code,
        signal: exit.signal,
        stdout,
        stderr,
        timedOut,
        ...(error === undefined ? {} : { error }),
      };
    });
  }

  spawn(command: string, args: readonly string[], options: RunOptions = {}): ChildHandle {
    const child = nodeSpawn(command, [...args], {
      cwd: options.cwd,
      env: options.env === undefined ? undefined : { ...options.env },
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });
    const stdoutListeners: Array<(text: string) => void> = [];
    const stderrListeners: Array<(text: string) => void> = [];
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (text: string) => stdoutListeners.forEach((listener) => listener(text)));
    child.stderr.on('data', (text: string) => stderrListeners.forEach((listener) => listener(text)));
    // A failed start emits 'error' and may also emit 'close'; a promise settles once, so
    // whichever arrives first is the answer and the other is ignored.
    const exited = new Promise<ProcessExit>((resolve) => {
      child.once('error', (error: Error) => {
        resolve({ code: null, signal: null, error: `${command}: ${error.message}` });
      });
      child.once('close', (code: number | null, signal: NodeJS.Signals | null) => {
        resolve({ code, signal });
      });
    });
    return {
      pid: child.pid,
      onStdout: (listener) => {
        stdoutListeners.push(listener);
      },
      onStderr: (listener) => {
        stderrListeners.push(listener);
      },
      exited,
      kill: (signal: NodeJS.Signals = 'SIGTERM') => child.kill(signal),
    };
  }

  launchDetached(
    command: string,
    args: readonly string[],
    options: RunOptions = {},
  ): Promise<{ readonly pid?: number; readonly error?: string }> {
    return new Promise((resolve) => {
      const child = nodeSpawn(command, [...args], {
        cwd: options.cwd,
        env: options.env === undefined ? undefined : { ...options.env },
        detached: true,
        shell: false,
        stdio: 'ignore',
        windowsHide: true,
      });
      child.once('error', (error: Error) => {
        resolve({ error: `${command}: ${error.message}` });
      });
      child.once('spawn', () => {
        child.unref();
        resolve({ pid: child.pid });
      });
    });
  }
}
