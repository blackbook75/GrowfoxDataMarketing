const path = require('path');
const { src, dest, series, parallel } = require('gulp');
const sass = require('gulp-dart-sass');
const localSass = require('sass');
const autoprefixer = require('gulp-autoprefixer');
const exec = require('gulp-exec');
const gulpIf = require('gulp-if');
const sourcemaps = require('gulp-sourcemaps');
const browserSync = require('browser-sync').create();
const useref = require('gulp-useref');
const webpack = require('webpack');
const log = require('fancy-log');
const colors = require('ansi-colors');
const rename = require('gulp-rename');

module.exports = (conf, srcGlob) => {
  // Build CSS
  // -------------------------------------------------------------------------------
  const buildCssTask = function (cb) {
    return src(srcGlob('**/*.scss', '!**/_*.scss'))
      .pipe(gulpIf(conf.sourcemaps, sourcemaps.init()))
      .pipe(
        // If sass is installed on your local machine, it will use command line to compile sass else it will use dart sass npm which 3 time slower
        gulpIf(
          localSass,
          exec(
            // If conf.minify == true, generate compressed style without sourcemap
            gulpIf(
              conf.minify,
              `sass --load-path=node_modules/ scss:${conf.distPath}/css fonts:${conf.distPath}/fonts libs:${conf.distPath}/libs --style compressed --no-source-map`,
              `sass --load-path=node_modules/ scss:${conf.distPath}/css fonts:${conf.distPath}/fonts libs:${conf.distPath}/libs --no-source-map`
            ),
            function (err) {
              cb(err);
            }
          ),
          sass
            .sync({
              includePaths: ['node_modules'], // Add this line to include node_modules
              outputStyle: conf.minify ? 'compressed' : 'expanded'
            })
            .on('error', sass.logError)
        )
      )
      .pipe(gulpIf(conf.sourcemaps, sourcemaps.write()))

      .pipe(
        rename(function (path) {
          path.dirname = path.dirname.replace('scss', 'css');
        })
      )
      .pipe(dest(conf.distPath))
      .pipe(browserSync.stream());
  };
  // Autoprefix css
  const buildAutoprefixCssTask = function (cb) {
    return src(conf.distPath + '/css/**/*.css')
      .pipe(
        gulpIf(
          conf.sourcemaps,
          sourcemaps.init({
            loadMaps: true
          })
        )
      )
      .pipe(autoprefixer())
      .pipe(gulpIf(conf.sourcemaps, sourcemaps.write()))
      .pipe(dest(conf.distPath + '/css'))
      .pipe(browserSync.stream());
  };

  // Build JS
  // -------------------------------------------------------------------------------
  const buildJsTask = function (cb) {
    setTimeout(function () {
      webpack(require('../webpack.config'), (err, stats) => {
        if (err) {
          log(colors.gray('Webpack error:'), colors.red(err.stack || err));
          if (err.details) log(colors.gray('Webpack error details:'), err.details);
          return cb();
        }

        const info = stats.toJson();

        if (stats.hasErrors()) {
          info.errors.forEach(e => log(colors.gray('Webpack compilation error:'), colors.red(e)));
        }

        if (stats.hasWarnings()) {
          info.warnings.forEach(w => log(colors.gray('Webpack compilation warning:'), colors.yellow(w)));
        }

        // Print log
        log(
          stats.toString({
            colors: colors.enabled,
            hash: false,
            timings: false,
            chunks: false,
            chunkModules: false,
            modules: false,
            children: true,
            version: true,
            cached: false,
            cachedAssets: false,
            reasons: false,
            source: false,
            errorDetails: false
          })
        );

        cb();
        browserSync.reload();
      });
    }, 1);
  };

  // Build fonts
  // -------------------------------------------------------------------------------

  const FONT_TASKS = [
    {
      name: 'flags',
      path: 'node_modules/flag-icons/flags/**/*'
    }
  ].reduce(function (tasks, font) {
    const functionName = `buildFonts${font.name.replace(/^./, m => m.toUpperCase())}Task`;
    const taskFunction = function () {
      // return src(root(font.path))
      return (
        src(font.path)
          // .pipe(dest(normalize(path.join(conf.distPath, 'fonts', font.name))))
          .pipe(dest(path.join(conf.distPath, 'fonts', font.name)))
      );
    };

    Object.defineProperty(taskFunction, 'name', {
      value: functionName
    });

    return tasks.concat([taskFunction]);
  }, []);

  // Formula module requires KaTeX - Quill Editor
  const KATEX_FONT_TASK = [
    {
      name: 'katex',
      path: 'node_modules/katex/dist/fonts/*'
    }
  ].reduce(function (tasks, font) {
    const functionName = `buildFonts${font.name.replace(/^./, m => m.toUpperCase())}Task`;
    const taskFunction = function () {
      return src(font.path).pipe(dest(path.join(conf.distPath, '/libs/quill/fonts')));
    };

    Object.defineProperty(taskFunction, 'name', {
      value: functionName
    });

    return tasks.concat([taskFunction]);
  }, []);

  const buildFontsTask = parallel(FONT_TASKS, KATEX_FONT_TASK);
  // Copy
  // -------------------------------------------------------------------------------

  const buildCopyTask = function () {
    return src(
      srcGlob(
        '**/*.png',
        '**/*.gif',
        '**/*.jpg',
        '**/*.jpeg',
        '**/*.svg',
        '**/*.swf',
        '**/*.eot',
        '**/*.ttf',
        '**/*.woff',
        '**/*.woff2'
      )
    ).pipe(dest(conf.distPath));
  };

  // Combine js vendor assets in single theme file using UseRef
  // -------------------------------------------------------------------------------
  const assetsBuildTasks = function () {
    return src(`${conf.buildTemplatePath}/*.html`).pipe(useref()).pipe(dest(conf.buildTemplatePath));
  };

  // Iconify task
  // -------------------------------------------------------------------------------
  const buildIconifyTask = function (cb) {
    // Create required directories without copying files
    const fs = require('fs');
    const directories = ['./fonts/iconify', './assets/vendor/fonts'];

    directories.forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });

    const iconify = require('child_process').spawn('node', ['./fonts/iconify/iconify.js']);

    iconify.stdout.on('data', data => {
      console.log(data.toString());
    });

    iconify.stderr.on('data', data => {
      console.error(data.toString());
    });

    iconify.on('close', code => {
      cb();
    });
  };

  const buildAllTask = series(buildCssTask, buildJsTask, buildFontsTask, buildCopyTask, buildIconifyTask);

  // Exports
  // ---------------------------------------------------------------------------

  return {
    css: series(buildCssTask, buildAutoprefixCssTask),
    js: buildJsTask,
    theme: assetsBuildTasks,
    fonts: buildFontsTask,
    copy: buildCopyTask,
    iconify: buildIconifyTask,
    all: buildAllTask
  };
};
