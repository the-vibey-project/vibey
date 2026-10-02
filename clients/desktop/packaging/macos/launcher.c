/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* The macOS app's main executable: points GTK's runtime at the bundle, then execs the program.
 *
 * GLib, GTK and gdk-pixbuf look for their schemas, icon themes, loaders and GIO modules where
 * Homebrew put them, which a Mac without Homebrew does not have. This sets the variables each
 * reads to the bundle's own copies, then replaces itself with the program (execv: the same
 * process, so the bundle's identity, its notifications and its window are the program's).
 *
 * gdk-pixbuf's loader cache names each loader by absolute path, and a bundle can live
 * anywhere (a mounted disk image, /Applications, ~/Applications). The bundle carries the
 * cache as a template; this writes it out, with the bundle's real path, to the per-user cache
 * directory. If that cannot be written, the program still runs: GTK draws PNG itself and
 * falls back to its own icons.
 *
 * Compiled by scripts/macos_app_bundle.py, which defines:
 *   KR_PROGRAM         the program's file name in Contents/MacOS
 *   KR_APP_ID          the app id, naming the cache directory
 *   KR_PIXBUF_TEMPLATE the loader cache template, relative to Contents/Resources
 *   KR_PIXBUF_DIR      the loaders' directory, relative to Contents/Resources
 *   KR_GIO_MODULE_DIR  the GIO modules' directory, relative to Contents/Resources
 *   KR_SCHEMA_DIR      the compiled schemas' directory, relative to Contents/Resources
 *   KR_PLACEHOLDER     the text in the template that stands for Contents/Resources
 */
#include <errno.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#if !defined(KR_PROGRAM) || !defined(KR_APP_ID) || !defined(KR_PIXBUF_TEMPLATE) ||             \
    !defined(KR_PIXBUF_DIR) || !defined(KR_GIO_MODULE_DIR) || !defined(KR_SCHEMA_DIR) ||        \
    !defined(KR_PLACEHOLDER)
#error "build this with scripts/macos_app_bundle.py, which defines the bundle's layout"
#endif

static void
fail(const char *what)
{
    fprintf(stderr, "krypton launcher: %s: %s\n", what, strerror(errno));
    exit(127);
}

static void
join(char *out, size_t size, const char *a, const char *b)
{
    if ((size_t) snprintf(out, size, "%s/%s", a, b) >= size) {
        errno = ENAMETOOLONG;
        fail(b);
    }
}

/* The template with every placeholder replaced by `resources`, or NULL. */
static char *
fill(const char *template_path, const char *resources)
{
    FILE *in = fopen(template_path, "rb");
    if (in == NULL)
        return NULL;
    if (fseek(in, 0, SEEK_END) != 0) {
        fclose(in);
        return NULL;
    }
    long length = ftell(in);
    rewind(in);
    if (length < 0) {
        fclose(in);
        return NULL;
    }
    char *text = malloc((size_t) length + 1);
    if (text == NULL || fread(text, 1, (size_t) length, in) != (size_t) length) {
        free(text);
        fclose(in);
        return NULL;
    }
    fclose(in);
    text[length] = '\0';

    size_t placeholder = strlen(KR_PLACEHOLDER), replacement = strlen(resources), count = 0;
    for (const char *at = strstr(text, KR_PLACEHOLDER); at != NULL;
         at = strstr(at + placeholder, KR_PLACEHOLDER))
        count++;
    char *out = malloc((size_t) length + count * replacement + 1);
    if (out == NULL) {
        free(text);
        return NULL;
    }
    char *write = out;
    const char *read = text;
    for (const char *at = strstr(read, KR_PLACEHOLDER); at != NULL;
         at = strstr(read, KR_PLACEHOLDER)) {
        memcpy(write, read, (size_t) (at - read));
        write += at - read;
        memcpy(write, resources, replacement);
        write += replacement;
        read = at + placeholder;
    }
    strcpy(write, read);
    free(text);
    return out;
}

/* Writes the filled loader cache under the per-user cache directory; its path, or NULL. */
static const char *
write_pixbuf_cache(const char *resources)
{
    static char cache[PATH_MAX];
    char template_path[PATH_MAX], user_cache[PATH_MAX], dir[PATH_MAX], partial[PATH_MAX];
    join(template_path, sizeof template_path, resources, KR_PIXBUF_TEMPLATE);
    if (confstr(_CS_DARWIN_USER_CACHE_DIR, user_cache, sizeof user_cache) == 0)
        return NULL;
    join(dir, sizeof dir, user_cache, KR_APP_ID);
    if (mkdir(dir, 0700) != 0 && errno != EEXIST)
        return NULL;
    join(cache, sizeof cache, dir, "loaders.cache");
    snprintf(partial, sizeof partial, "%s.%ld", cache, (long) getpid());

    char *text = fill(template_path, resources);
    if (text == NULL)
        return NULL;
    FILE *out = fopen(partial, "wb");
    if (out == NULL) {
        free(text);
        return NULL;
    }
    size_t length = strlen(text);
    int written = fwrite(text, 1, length, out) == length;
    free(text);
    if (fclose(out) != 0 || !written || rename(partial, cache) != 0) {
        unlink(partial);
        return NULL;
    }
    return cache;
}

int
main(int argc, char **argv)
{
    (void) argc;
    char raw[PATH_MAX], self[PATH_MAX];
    uint32_t size = sizeof raw;
    if (_NSGetExecutablePath(raw, &size) != 0 || realpath(raw, self) == NULL)
        fail("cannot find its own path");

    /* self is .../Name.app/Contents/MacOS/Name: Contents is two levels up. */
    char macos[PATH_MAX], contents[PATH_MAX], resources[PATH_MAX];
    strcpy(macos, self);
    char *slash = strrchr(macos, '/');
    if (slash == NULL)
        fail("its path has no directory");
    *slash = '\0';
    strcpy(contents, macos);
    slash = strrchr(contents, '/');
    if (slash == NULL)
        fail("it is not inside an app bundle");
    *slash = '\0';
    join(resources, sizeof resources, contents, "Resources");

    char share[PATH_MAX], schemas[PATH_MAX], modules[PATH_MAX], loaders[PATH_MAX];
    join(share, sizeof share, resources, "share");
    join(schemas, sizeof schemas, resources, KR_SCHEMA_DIR);
    join(modules, sizeof modules, resources, KR_GIO_MODULE_DIR);
    join(loaders, sizeof loaders, resources, KR_PIXBUF_DIR);
    if (setenv("XDG_DATA_DIRS", share, 1) != 0 || setenv("GSETTINGS_SCHEMA_DIR", schemas, 1) != 0 ||
        setenv("GIO_MODULE_DIR", modules, 1) != 0 ||
        setenv("GDK_PIXBUF_MODULEDIR", loaders, 1) != 0)
        fail("cannot set the runtime's paths");
    const char *cache = write_pixbuf_cache(resources);
    if (cache != NULL && setenv("GDK_PIXBUF_MODULE_FILE", cache, 1) != 0)
        fail("cannot set the loader cache");

    char program[PATH_MAX];
    join(program, sizeof program, macos, KR_PROGRAM);
    argv[0] = program;
    execv(program, argv);
    fail(program);
    return 127;
}
