import os
from django.core.management.base import CommandError
from django.core.management.commands import makemessages


def os_path(path: str):
    if os.name == 'nt':
        return path.replace('/', '\\')
    return path.replace('\\', '/')


def os_paths(paths: list[str]):
    return list(map(lambda x: os_path(x), paths))


class Command(makemessages.Command):
    domain: str
    _domain: str
    include_dirs = []

    def handle(self, *args, **options):
        ignore_patterns = ['.venv/*']

        print('processing domain django')
        self._domain = 'django'
        options['ignore_patterns'] = os_paths(ignore_patterns + ['handlers/*'])
        super().handle(*args, **options)

        print('processing domain bot')
        self._domain = 'bot'
        options['ignore_patterns'] = os_paths(ignore_patterns + ['app/*'])
        self.include_dirs = os_paths(['bot/handlers'])
        super().handle(*args, **options)

    def build_potfiles(self):
        self.domain = self._domain
        return super().build_potfiles()

    def process_files(self, file_list):
        if self.include_dirs:
            file_list = [self.find_files(path) for path in self.include_dirs]
            file_list = [file for files in file_list for file in files]
        super().process_files(file_list)

    def process_locale_dir(self, locale_dir, files):
        build_files = []
        for translatable in files:
            if self.verbosity > 1:
                self.stdout.write(
                    "processing file %s in %s"
                    % (translatable.file, translatable.dirpath)
                )
            build_file = self.build_file_class(self, self.domain, translatable)
            try:
                build_file.preprocess()
            except UnicodeDecodeError as e:
                self.stdout.write(
                    "UnicodeDecodeError: skipped file %s in %s (reason: %s)"
                    % (
                        translatable.file,
                        translatable.dirpath,
                        e,
                    )
                )
                continue
            except BaseException:
                # Cleanup before exit.
                for build_file in build_files:
                    build_file.cleanup()
                raise
            build_files.append(build_file)

        args = [
            "xgettext",
            "-d",
            self.domain,
            "--language=Python",
            "--keyword=gettext_noop",
            "--keyword=gettext_noop",
            "--keyword=gettext_lazy",
            "--keyword=ngettext_lazy:1,2",
            "--keyword=pgettext:1c,2",
            "--keyword=npgettext:1c,2,3",
            "--keyword=pgettext_lazy:1c,2",
            "--keyword=npgettext_lazy:1c,2,3",
            "--output=-",
        ]

        if self.domain == 'bot':
            args.append("--keyword=bgettext")

        input_files = [bf.work_path for bf in build_files]
        with makemessages.NamedTemporaryFile(mode="w+") as input_files_list:
            input_files_list.write("\n".join(input_files))
            input_files_list.flush()
            args.extend(["--files-from", input_files_list.name])
            args.extend(self.xgettext_options)
            msgs, errors, status = makemessages.popen_wrapper(args)

        if errors:
            if status != makemessages.STATUS_OK:
                for build_file in build_files:
                    build_file.cleanup()
                raise CommandError(
                    "errors happened while running xgettext on %s\n%s"
                    % ("\n".join(input_files), errors)
                )
            elif self.verbosity > 0:
                self.stdout.write(errors)

        if msgs:
            if locale_dir is makemessages.NO_LOCALE_DIR:
                for build_file in build_files:
                    build_file.cleanup()
                file_path = os.path.normpath(build_files[0].path)
                raise CommandError(
                    "Unable to find a locale path to store translations for "
                    "file %s. Make sure the 'locale' directory exists in an "
                    "app or LOCALE_PATHS setting is set." % file_path
                )
            for build_file in build_files:
                msgs = build_file.postprocess_messages(msgs)
            potfile = os.path.join(locale_dir, "%s.pot" % self.domain)
            makemessages.write_pot_file(potfile, msgs)

        for build_file in build_files:
            build_file.cleanup()
