# Default CI templates

This repo contains a series of templates that is used inside the CI/CD pipeline of JTM.

The syntax here is valid for a Gitlab CI setup. Our current version of Gitlab is 12.9.0

At Jobtome, we use GCP as our Cloud provider, hence you can imagine a lot of pipelines are related/applicable to GCP. Also, we use three main regions for our services, so you will see a lot of references about that distinction.

We manage our GCP infrastructure through Terraform, thus you can find also terraform-related pipeline files. Have a look at our [tf GCP modules](https://github.com/jobtome-labs/terraform-modules), too, if you also manage GCP through Terraform!

## Pipeline order and workflow

With Kubernetes:

`lint -> build -> test -> push -> manifest -> deploy -> rollback -> notify`

With Helm:

`lint -> build -> test -> push -> deploy -> verify -> notify`


Our workflow:
- A commit on master goes to quality
- A tag on master promotes to production

### Folder structure
For kubernetes regional projects:
```
my-project
|_ src
|_ kube
   |_production
      \_hpa.yaml
   |_quality
      \_hpa.yaml
  \_deployment.yaml
  \_other-files-common-to-prod-and-qa.yaml
.gitlab.ci.yml
...other files
```

For kubernetes multiregional projects:
```
my-project
|_ src
|_ kube
   |_production
     |_production_asia
        \_hpa.yaml
     |_production_america
        \_hpa.yaml
     |_production_europe
        \_hpa.yaml
   |_quality
      \_hpa.yaml
  \_deployment.yaml
  \_other-files-common-to-prod-and-qa.yaml
.gitlab.ci.yml
...other files
```

For terraform projects:
```
my-project
|_ platform
  \_main.tf
  \_output.tf
  ...
.gitlab.ci.yml
...
```

### How to use it

According to the operation / the type of pipeline you have to perform, you can pick here different stages, and put the snippet as indicated in your `.gitlab-ci.yml`:

- [Linting](#linting)
- Tests
  - [Docker-compose tests](#unit-test-stage)
  - [API tests](#api-test-stage)
- [Docker pipeline](#docker-pipeline)
  - Build
  - Test for image vulnerabilities
  - Push to registry
- Kubernetes deployment
  - [Deploy on quality (a.k.a. staging)](#kubernetes-quality-pipeline)
  - [Regional deployment](#kubernetes-regional-pipeline)
  - [Multi-regional deployment](#kubernetes-multiregion-pipeline)
  - ["Simple script" execution](#kubernetes-"simple-script"-pipeline)
  - [Note on configmaps](#note-on-configmaps)
- [Helm deployment](#helm-deployment)
- [Helm chart publishing](#helm-chart-publishing)
- [SSH command](#ssh-command)
- [Publishing on calendar](#publish-to-google-calendar-and-slack)
- [Google bucket upload](#deploy-to-google-storage)
- Serverless functions deployment
  - [Quality deployment](#google-function-quality-pipeline)
  - [Regional deployment](#google-function-regional-pipeline)
  - [Multi-regional deployment](#google-function-multiregion-pipeline)
- [Google endpoint](#google-endpoint)
- Google cloud run
  - [Quality pipeline](#google-cloud-run-quality)
  - [Production pipeline](#google-cloud-run-production)
- [Google dataflow](#dataflow)
- [Terraform pipeline](#terraform-pipeline)
- [Terraform security check](#terraform-security-score)
- [Notify sentry of release](#notify-sentry-of-release)

Finally some [advice](#general-advices) on how to try the pipeline (for development).

### How to use it

If you're an operations team, a devops, or if you know very well what you're doing, copy the relevant part from this readme to your `.gitlab-ci.yml` file. You can also override some operations by overriding the stages or the operation itself.

A note on gitlab-ci syntax:

```yaml
include:
  - project: 'group/reponame'
    ref: v1.0.2
    file: 'test-unit.yml'
```

will import the code from another Gitlab project

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/test-unit.yml'
```

will import the code from an external repository; notice ref and filename are embedded into the URL.

**Throughout the readme, the tag section will be a placeholder**.

## Linting

The stage `lint` will perform at least 2 checks:
- lint:docker (checks the Dockerfile(s) against good practices)
- lint:yaml (checks the yaml format of the manifests against good practices)

Additionally it will perform the linting of the selected languages. All is needed to do is to specify the file to import as `lint-go.yml` or `lint-php.yml`.

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/lint-go.yml'

stages:
  - lint

variables:
  # optional, used by docker-lint
  IGNORE_DOCKER_LINT: "DL3012"

  # optional, used to enable reviewdog
  ENABLE_REVIEWDOG: 1
  REVIEWDOG_GITLAB_API_TOKEN: <personal gitlab token used to call v4 api endpoints>
  REVIEWDOG_LEVEL: warning # optional, values: info, warning, error
```

The [Review Dog](https://github.com/reviewdog/reviewdog) feature provides a way to post review comments automatically by integrating with any linter tools with ease. It uses an output of lint tools and posts them as a comment if findings are in diff of patches to review.

The default skipped test for `lint-docker` is `Provide an email address or URL as maintainer`. See skippable tests [here](https://hub.docker.com/r/hadolint/hadolint).

If one wants to check the kube manifests (through lint and security practices), then the import becomes `test-kubernetes-score.yaml`, and it will perform the following:

- lint:kubernetes (checks the object's manifests against their schema)
- test:kubernetes-score (checks the manifests against good practices)

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/test-kubernetes-score.yml'

stages:
  - lint

variables:
  #optional, used by kube-score
  IGNORE_TESTS: "container-security-context pod-networkpolicy label-values"
```

Notice by default three kube-score tests are excluded (the ones indicated above). If you want to run it 'strict', do declare `IGNORE_TESTS` as empty string; otherwise you can avoid declaring it.

See [here](https://github.com/zegl/kube-score/blob/master/README_CHECKS.md) for skippable tests.

NB: The test `label_values` needs to be skipped because of the values `${CI_COMMIT_TAG}` (which will be replaced by `envsubst` later in the pipeline) causing validation fail.

### Linting shell files

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/lint-shell.yml'

stages:
  - lint

variables:
  # optional, used to enable reviewdog
  ENABLE_REVIEWDOG: 1
  REVIEWDOG_GITLAB_API_TOKEN: <personal gitlab token used to call v4 api endpoints>
  REVIEWDOG_LEVEL: warning # optional, values: info, warning, error
```

### Linting python files

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/lint-python.yml'

stages:
  - lint

variables:
  IGNORE_PYTHON_LINT: "E10,D11,I12" #@see https://flake8.pycqa.org/en/latest/user/violations.html
```

The docker image allows use with reviewdog, like above, but the code has not been added yet. Contributions are welcome

# Unit test stage

```yaml
include:
  remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/test-unit.yml'

stages:
  - test

variables:
  TEST_CONTAINER_NAME: "app" #Default value
  COMPOSER_FILE_NAME: "docker-compose.test.yml" #Default value
```

This assumes testing to be done on the containerised application.
This will spin up a `docker-compose.test.yml` and check the exit code of the container `app`. If the file is not named `docker-compose.test.yml`, or the test container is not named `app`, the variables are there to correct the names.

# API test stage

```yaml
include:
  remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/test-api.yml'

stages:
  - test

variables:
  TEST_FOLDER: "tests" #Default value
  THREADS: "3" #Default value
```

This will run all the test definitions defined with BDD-syntax into [karate](https://github.com/intuit/karate)

## Docker pipeline

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/docker.yml'

stages:
  - build
  - test
  - push

variables:
  IMAGES: "app nginx"
  STAGES: "build assets"
  DOCKERFILES_DIR: "docker"
  SKIP_DOCKER_CACHE: "false"
  DOCKER_NAME_CONTAINS_BRANCH: "true" #optional
```

All stages in Docker file should be named (e.g. `AS buildes`, `AS prod`...). These need to be added to `STAGES` variable. `IMAGES` variable defines the images that will be built, just delete the variable if a single image will be created. In this case the image will be named as `CI_REGISTRY_IMAGE`, othewise `CI_REGISTRY_IMAGE` will be a folder containing `IMAGES`.
`DOCKERFILES_DIR` is used to specify a different folder containing Dockerfiles instead of the default root directory.

This will spawn a job `build` and a job `build:cache`. NOTE: The cache created at pipeline N is used for the pipeline N+1

By enabling the flag `DOCKER_NAME_CONTAINS_BRANCH`, every branch built (so, by default, a branch which is undergoing MR) will have its own registry image in the following format:
`registry.example.com/repo-path/repo-name/branch:tag` or `registry.example.com/repo-path/repo-name/branch/image:tag` (master branch is excluded from this).
This is opposed to the 'usual'
`registry.example.com/repo-path/repo-name:tag` or
`registry.example.com/repo-path/repo-name/image:tag` (where classically, image:={app|nginx})

NB: when using this flag, remember that the gitlab's registry cleanup policy happens *per-directory* and not *globally* inside a project's registry.

### Alternative multi-stage build / caching

`.docker:build:multi` template allows building a particular stage of a multi-stage Dockerfile with an optional cache facility. Unlike the other pipeline template, this cache is used within the same pipeline

One can add the following to the .gitlab-ci:

```
stages:
  ...
  - build-cache # new!
  - build
  ...


# this step should be run before running any other steps so that it results in a cached image that can be re-used in the next build stage
build-cache:
  extends: .docker:build:multi
  stage: build-cache
  variables:
    # target stage name
    BUILD_TARGET: base
    # tag suffix to produce
    IMAGE_TAG_SUFFIX: base

build-prod:
  extends: .docker:build:multi
  stage: build
  variables:
    # defines the suffix of the cache image
    CACHE_FROM: base
    BUILD_TARGET: prod
    # note, no IMAGE_TAG_SUFFIX defined - this will be the main image in the repo

build-debug:
  extends: .docker:build:multi
  stage: build
  variables:
    CACHE_FROM: base
    BUILD_TARGET: debug
    IMAGE_TAG_SUFFIX: debug

build-nginx:
  extends: .docker:build:multi
  stage: build
  variables:
    # note, no CACHE_FROM defined - this will be built without cache
    BUILD_TARGET: nginx
    IMAGE_TAG_SUFFIX: nginx
```

In natural language: there's a pipeline stage `build-cache` where the docker stage is built, and the following `build` pipeline stage has 3 jobs using the pre-built docker stage.

```
.docker:build:multi:
  extends: .docker
  stage: build
  #variables:
    #### Supported vars
    #CACHE_FROM: base
    #IMAGE_TAG_SUFFIX: debug
    #BUILD_TARGET: prod
```

NOTE: this job assumes that the Dockerfile is ONE, and in the root of the project.

This job does not override the jobs described above: to remove jobs `build` and `build:cache`, add to the .gitlab.ci.yml an override to never run them.

Additionally, this job *by default* creates a docker image for every branch (see end of previous section)

## Kubernetes quality pipeline

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/kubernetes-quality.yml'

stages:
  - build
  - push
  - manifest
  - deploy
  - rollback

variables:
  IMAGES: "app nginx"
  ROLLOUT_RESOURCES: "deployment/app deployment/worker"

  # QUALITY VARIABLES
  GOOGLE_KEY_QUALITY: <google json key>
  NAMESPACE_QUALITY: "my-namespace"
  CLUSTER_NAME_QUALITY: quality
  CLUSTER_ZONE_QUALITY: europe-west6-a
  SECRET_YAML_QUALITY: <secret base64 encoded>
  DOMAIN_QUALITY: quality.example.com
```

## Kubernetes regional pipeline

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/kubernetes-regional.yml'

stages:
  - build
  - push
  - manifest
  - deploy
  - rollback

variables:
  IMAGES: "app nginx"
  ROLLOUT_RESOURCES: "deployment/app"

  # QUALITY VARIABLES
  GOOGLE_KEY_QUALITY: <google json key>
  NAMESPACE_QUALITY: "my-namespace"
  CLUSTER_NAME_QUALITY: quality
  CLUSTER_ZONE_QUALITY: europe-west6-a
  SECRET_YAML_QUALITY: <secret base64 encoded>
  DOMAIN_QUALITY: quality.example.com

  # PRODUCTION VARIABLES
  GOOGLE_KEY_PRODUCTION: <google json key>
  NAMESPACE_PRODUCTION: "my-namespace"
  CLUSTER_NAME_PRODUCTION: production-europe-west1
  CLUSTER_ZONE_PRODUCTION: europe-west1-b
  SECRET_YAML_PRODUCTION: <secret base64 encoded>
  DOMAIN_PRODUCTION: production.example.com
```

## Kubernetes multiregion pipeline

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/kubernetes-multiregion.yml'

stages:
  - build
  - push
  - manifest
  - deploy
  - rollback

variables:
  IMAGES: "app nginx"
  ROLLOUT_RESOURCES: "deployment/app"

  # QUALITY VARIABLES
  GOOGLE_KEY_QUALITY: <google json key>
  NAMESPACE_QUALITY: "my-namespace"
  CLUSTER_NAME_QUALITY: quality
  CLUSTER_ZONE_QUALITY: europe-west6-a
  SECRET_YAML_QUALITY: <secret base64 encoded>
  DOMAIN_QUALITY: quality.example.com

  # PRODUCTION EUROPE VARIABLES
  GOOGLE_KEY_PRODUCTION_EUROPE: <google json key>
  NAMESPACE_PRODUCTION_EUROPE: "my-namespace"
  CLUSTER_NAME_PRODUCTION_EUROPE: production-europe-west1
  CLUSTER_ZONE_PRODUCTION_EUROPE: europe-west1-b
  SECRET_YAML_PRODUCTION_EUROPE: <secret base64 encoded>
  DOMAIN_PRODUCTION_EUROPE: eu.production.example.com

  # PRODUCTION AMERICA VARIABLES
  GOOGLE_KEY_PRODUCTION_AMERICA: <google json key>
  NAMESPACE_PRODUCTION_AMERICA: "my-namespace"
  CLUSTER_NAME_PRODUCTION_AMERICA: production-us-central1
  CLUSTER_ZONE_PRODUCTION_AMERICA: us-central1-a
  SECRET_YAML_PRODUCTION_AMERICA: <secret base64 encoded>
  DOMAIN_PRODUCTION_AMERICA: am.production.example.com

  # PRODUCTION ASIA VARIABLES
  GOOGLE_KEY_PRODUCTION_ASIA: <google json key>
  NAMESPACE_PRODUCTION_ASIA: "my-namespace"
  CLUSTER_NAME_PRODUCTION_ASIA: production-asia-east1
  CLUSTER_ZONE_PRODUCTION_ASIA: asia-east1-a
  SECRET_YAML_PRODUCTION_ASIA: <secret base64 encoded>
  DOMAIN_PRODUCTION_ASIA: as.production.example.com
```

### Note on configmaps
In order to deploy configmaps at every run (not just after the manual stage of "manifest") one can use this code:

1. Remember to add among the `variables:` the `BEFORE_CUSTOM_APPLY_FILE_PATH: "/tmp/before-manifest.yaml"`
2. Use the following snippet for regional deployments

```yaml
deploy:quality:image:
  before_script:
    - &deployconfig |
      # DEPLOY CONFIGMAP PHASE

      if [ -z "${ENVIRONMENT}" ]; then
        ENVIRONMENT=production
      fi

      if [ -z "${KUBERNETES_DIR}" ]; then
        KUBERNETES_DIR=kube
      fi

      envsubst < "${KUBERNETES_DIR}"/"${ENVIRONMENT}"/configmap.yaml >> "${BEFORE_CUSTOM_APPLY_FILE_PATH}"

deploy:production:image:
  before_script:
    - *deployconfig
```

If the deployment is not regional but multiregional, use this [NB there are more variables to add in this case, such as `ENVIRONMENT_PATH_ASIA; ENVIRONMENT_PATH_EUROPE; ENVIRONMENT_PATH_AMERICA`]:

```yaml
deploy:quality:image:
  before_script:
    - &deployconfig |
      # DEPLOY CONFIGMAP PHASE

      if [ -z "${ENVIRONMENT}" ]; then
        ENVIRONMENT=production
      fi

      if [ "${ENVIRONMENT}" != "quality" ]; then
        if [ "${ENVIRONMENT_NAME}" == "production-asia" ]; then
          ENVIRONMENT="${ENVIRONMENT_PATH_ASIA}"
        fi
        if [ "${ENVIRONMENT_NAME}" == "production-europe" ]; then
          ENVIRONMENT="${ENVIRONMENT_PATH_EUROPE}"
        fi
        if [ "${ENVIRONMENT_NAME}" == "production-america" ]; then
          ENVIRONMENT="${ENVIRONMENT_PATH_AMERICA}"
        fi
      fi

      if [ -z "${KUBERNETES_DIR}" ]; then
        KUBERNETES_DIR=kube
      fi

      envsubst < "${KUBERNETES_DIR}"/"${ENVIRONMENT}"/configmap.yaml >> "${BEFORE_CUSTOM_APPLY_FILE_PATH}"

deploy:production:asia:image:
  before_script:
    - *deployconfig

deploy:production:america:image:
  before_script:
    - *deployconfig

deploy:production:europe:image:
  before_script:
    - *deployconfig
```

### Note on secrets
As of version v2.29.1 of the pipelines, Mozilla SOPS has been introduced to take care of secrets *inside of repositories* (encrypted).
On the human side, don't forget to put git hooks to avoid commit of plaintext secrets.
On the tech side, in order to use this new feature (which is optional), one needs to add in the gitlab variables a SOPS_KEY (a json of a service account with `Cloud KMS CryptoKey Decrypter` permission on the key), and a SOPS_CONF (containing the `.sops.yaml` configuration).


## Kubernetes run script quality

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/kubernetes-task-quality.yml'

stages:
  - deploy

variables:
  GOOGLE_PROJECT: my-project

  # QUALITY VARIABLES
  NAMESPACE_QUALITY: my-namespace
  GOOGLE_KEY_QUALITY: <google json key>
  CLUSTER_NAME_QUALITY: quality-europe-west1
  CLUSTER_ZONE_QUALITY: europe-west1-b
  KUBERNETES_SCRIPT_QUALITY: kupdate statefulset resource-name
```

If there is only one argument, then the resource type "deployment" is intended. Explicitly give a different resource type e.g. "statefulset" in other cases.

## Kubernetes run script production

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/kubernetes-task-production.yml'

stages:
  - deploy

variables:
  GOOGLE_PROJECT: my-project

  # QUALITY VARIABLES
  NAMESPACE_QUALITY: my-namespace
  GOOGLE_KEY_QUALITY: <google json key>
  CLUSTER_NAME_QUALITY: quality-europe-west1
  CLUSTER_ZONE_QUALITY: europe-west1-b
  KUBERNETES_SCRIPT_QUALITY: kupdate statefulset resource-name

  # QUALITY VARIABLES
  NAMESPACE_QUALITY: my-namespace
  GOOGLE_KEY_PRODUCTION: <google json key>
  CLUSTER_NAME_PRODUCTION: production-europe-west1
  CLUSTER_ZONE_PRODUCTION: europe-west1-b
  KUBERNETES_SCRIPT_PRODUCTION: kupdate statefulset resource-name
```

If there is only one argument, then the resource type "deployment" is intended. Explicitly give a different resource type e.g. "statefulset" in other cases.

## Helm deployment

Just like k8s, but with some additional variables

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/helm-{quality|regional|multiregion}.yml'

stages:
  - build
  - push
  - deploy
  - verify

variables:
  IMAGES: "app nginx"
  APP_NAME: "myapp"
  GOOGLE_PROJECT: "my-project"
  CHARTS_URL: "https://my-chart-bucket-name.cloudstorage.provider.com"
  CHART_NAME: "my-app-chart"
  CHART_VERSION: "1.2.3" #optional, defaults to latest in chart repo


  # QUALITY VARIABLES
  CLUSTER_NAME_QUALITY: quality
  CLUSTER_ZONE_QUALITY: europe-west1-b
  DOMAIN_QUALITY: quality.example.com
  NAMESPACE_QUALITY: "my-namespace"

  # if needed:
  # PRODUCTION EUROPE VARIABLES
  ...
  # PRODUCTION AMERICA VARIABLES
  ...
  # PRODUCTION ASIA VARIABLES
  ...
```

In addition to these features, starting from `v2.29.3` you can enable review app on merge requests by including in the remotes:
```
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/helm-branches.yaml'
```
and adding as the *last* stage `- stop`.

Doing so will create a new helm deployment in QA based on the commit slug when the branch name starts with "feat". Once you're done, the branch deployment will be automatically deleted. This requires also to set up a values.yaml in the helm/feature/ folder (you may juspy quality one as a starting point).

You need to place a helm/feature/values.yaml manifest to be used in helm deployment in feature branches. Initially you can copy/paste quality one, you can customize configmaps here to be review-app specific. You can also create a feature branch specific secret as a Gitlab CI/CD variable called SECRET_YAML_FEATURE, or an even more specific secret defined in gitlab-ci.yml as SECRET_BRANCH=whateverspecificsecretyouwant. Just please, use a a different "name:" for the configmap and the secrets, in order to avoid overwriting quality ones when appropriate.

Branch domain and app name can be overriden in gitlab-ci.yml using these variables:

DOMAIN_BRANCH: "mydomain.tld"
APP_NAME_BRANCH: "myapp"


### Helm chart publishing

This is for a repository which holds a Helm chart. It is triggered at every tag.

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/helm-publish.yml'

stages:
  - push

variables:
  GOOGLE_PROJECT: "my-project"
  BUCKET_NAME: "my-charts"
  BUCKET_HEADERS: "Cache-Control:no-cache, max-age=0"
  BUCKET_PATH: ""
```

## SSH command

This is for a repository which need to deploy through ssh.

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/ssh-production.yml'

stages:
  - deploy

variables:
  SSH_PRIVATE_KEY_QUALITY: <ssh key base64 encoded>
  SSH_USER_QUALITY: admin
  SSH_HOST_QUALITY: quality.example.com
  SSH_COMMAND_QUALITY: ansible-playbook -i quality  app.yml'
  SSH_KNOWN_HOSTS_QUALITY: <known hosts file base64 encoded>
  DOMAIN_QUALITY: quality.example.com

  SSH_PRIVATE_KEY_PRODUCTION: <ssh key base64 encoded>
  SSH_USER_PRODUCTION: admin
  SSH_HOST_PRODUCTION: production.example.com
  SSH_COMMAND_PRODUCTION: ansible-playbook -i production app.yml'
  SSH_KNOWN_HOSTS_PRODUCTION: <known hosts file base64 encoded>
  DOMAIN_PRODUCTION: production.example.com
```

## Publish to Google Calendar and Slack

We have an internal calendar where we track deployments (and maintenances and incidents through another tool). At the end of the pipeline, this stage is triggered only on success.

We use a 3rd-party tool called [GAM](https://github.com/jay0lee/GAM) for this.

For slack, we use a simple webhook.

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/notify.yml'

stages:
  - notify

variables:
  GOOGLE_CALENDAR_ID: <calendar ID>
  OAUTH2SERVICE: <see gam help>
  OAUTH2TXT: <see gam help>
  CLIENTSECRETS: <see gam help>
  SLACK_WEBHOOK_URL: <url>
```

## Deploy to Google Storage

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/bucket-production.yml'

stages:
  - deploy

variables:
  GOOGLE_PROJECT: my-project
  SYNC_MODE: copy
  DIR_TO_SYNC: public
  BUCKET_PATH: data
  GOOGLE_KEY_QUALITY: <google json key>
  GOOGLE_KEY_PRODUCTION: <google json key>
  BUCKET_NAME_QUALITY: test.website.com
  BUCKET_NAME_PRODUCTION: website.com
  BUCKET_HEADERS_QUALITY: "Cache-Control:no-cache,max-age=0"
  BUCKET_HEADERS_PRODUCTION: "Cache-Control:public,max-age=3600"
```

If unset, `GOOGLE_PROJECT` defaults to `my-project`

If unset, `SYNC_MODE` defaults to `rsync`

If unset, `DIR_TO_SYNC` defaults to `.`

If unset, `BUCKET_PATH` defaults to `data`

**NOTE: if you set "BUCKET_PATH" variable to '' and the "SYNC_MODE" variable is set to rsync you'll lose all bucket data**

## Google function quality pipeline

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/serverless-quality.yml'

stages:
  - deploy

variables:
  RUNTIME: go111
  TRIGGER_HTTP: 1
  TIMEOUT: 30
  ENTRYPOINT: main
  EXTRA_FLAGS: "--vpc-connector serverless" # In case there are specific flags/features to use

  # QUALITY VARIABLES
  SERVICE_ACCOUNT_QUALITY: default
  FUNCTION_NAME_QUALITY: my-function
  GOOGLE_KEY_QUALITY: <google json key>
  REGION_QUALITY: europe-west1
  TRIGGER_TOPIC_QUALITY: topic-qa
  DOMAIN_QUALITY: https://us-central1.cloudfunctions.net/http_function
  SECRET_YAML_QUALITY: <secret base64 encoded>
  SECRET_ENV_LIST_QUALITY: "SUPERSECRET=env"
```

## Google function regional pipeline

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/serverless-regional.yml'

stages:
  - deploy

variables:
  RUNTIME: go111
  TRIGGER_HTTP: 1
  TIMEOUT: 30
  ENTRYPOINT: main
  EXTRA_FLAGS: "--vpc-connector serverless" # In case there are specific flags/features to use

  # QUALITY VARIABLES
  SERVICE_ACCOUNT_QUALITY: default
  FUNCTION_NAME_QUALITY: my-function
  GOOGLE_KEY_QUALITY: <google json key>
  REGION_QUALITY: europe-west1
  TRIGGER_TOPIC_QUALITY: topic-qa
  DOMAIN_QUALITY: https://us-central1.cloudfunctions.net/http_function
  SECRET_YAML_QUALITY: <secret base64 encoded>
  SECRET_ENV_LIST_QUALITY: "SUPERSECRET=env"

  # PRODUCTION VARIABLES
  SERVICE_ACCOUNT_PRODUCTION: default
  FUNCTION_NAME_PRODUCTION: my-function
  REGION_PRODUCTION: europe-west1
  TRIGGER_TOPIC_PRODUCTION: topic
  GOOGLE_KEY_PRODUCTION: <google json key>
  DOMAIN_PRODUCTION: https://us-central1.cloudfunctions.net/http_function
  SECRET_YAML_PRODUCTION: <secret base64 encoded>
  SECRET_ENV_LIST_PRODUCTION: "SUPERSECRET=env"
```

## Google function multiregion pipeline

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/serverless-multiregional.yml'

stages:
  - deploy

variables:
  RUNTIME: go111
  TRIGGER_HTTP: 1
  TIMEOUT: 30
  ENTRYPOINT: main
  EXTRA_FLAGS: "--vpc-connector serverless" # In case there are specific flags/features to use

  # QUALITY VARIABLES
  SERVICE_ACCOUNT_QUALITY: default
  FUNCTION_NAME_QUALITY: my-function
  GOOGLE_KEY_QUALITY: <google json key>
  REGION_QUALITY: europe-west1
  TRIGGER_TOPIC_QUALITY: topic-qa
  DOMAIN_QUALITY: https://us-central1.cloudfunctions.net/http_function
  SECRET_YAML_QUALITY: <secret base64 encoded>
  SECRET_ENV_LIST_QUALITY: "SUPERSECRET=env"

  # PRODUCTION EUROPE VARIABLES
  SERVICE_ACCOUNT_PRODUCTION_EUROPE: default
  FUNCTION_NAME_PRODUCTION_EUROPE: my-function
  GOOGLE_KEY_PRODUCTION_EUROPE: <google json key>
  REGION_PRODUCTION_EUROPE: europe-west1
  TRIGGER_TOPIC_PRODUCTION_EUROPE: topic-eu
  DOMAIN_PRODUCTION_EUROPE: https://europe-west1.cloudfunctions.net/http_function
  SECRET_YAML_PRODUCTION_EUROPE: <secret base64 encoded>
  SECRET_ENV_LIST_PRODUCTION_EUROPE: "SUPERSECRET=env"

  # PRODUCTION AMERICA VARIABLES
  SERVICE_ACCOUNT_PRODUCTION_AMERICA: default
  FUNCTION_NAME_PRODUCTION_AMERICA: my-function
  GOOGLE_KEY_PRODUCTION_AMERICA: <google json key>
  REGION_PRODUCTION_AMERICA: us-central1
  TRIGGER_TOPIC_PRODUCTION_AMERICA: topic-am
  DOMAIN_PRODUCTION_AMERICA: https://us-central1.cloudfunctions.net/http_function
  SECRET_YAML_PRODUCTION_AMERICA: <secret base64 encoded>
  SECRET_ENV_LIST_PRODUCTION_AMERICA: "SUPERSECRET=env"

  # PRODUCTION ASIA VARIABLES
  SERVICE_ACCOUNT_PRODUCTION_ASIA: default
  FUNCTION_NAME_PRODUCTION_ASIA: my-function
  GOOGLE_KEY_PRODUCTION_ASIA: <google json key>
  REGION_PRODUCTION_ASIA: asia-east2
  TRIGGER_TOPIC_PRODUCTION_ASIA: topic-as
  DOMAIN_PRODUCTION_ASIA: https://asia-east2.cloudfunctions.net/http_function
  SECRET_YAML_PRODUCTION_ASIA: <secret base64 encoded>
  SECRET_ENV_LIST_PRODUCTION_ASIA: "SUPERSECRET=env"
```

## Google endpoint

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/endpoint.yml'

stages:
  - test
  - deploy

variables:
  ENDPOINT_FILE: endpoint.yaml
  GOOGLE_KEY: <google json key>
```
## Google Cloud Run Quality

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/cloudrun-quality.yml'

stages:
  - deploy

variables:
  GOOGLE_KEY_QUALITY: <google json key>
  GOOGLE_PROJECT: my-project
  CLUSTER_NAME_QUALITY: "quality"
  CLUSTER_ZONE_QUALITY: "europe-west1-b"
  NAMESPACE: my-k8s-namespace-where-cloudrun-is
  SERVICE_NAME: awesome-service
  CONNECTIVITY: "external"
  TIMEOUT: "60s"
  CONCURRENCY: "80"
  CPU: "1000m"
  MEMORY: "128M"
  MAX_INSTANCES: "3"
  ENV_QUALITY: "KEY1=value1,KEY2=value2"
  SECRET_YAML_QUALITY: <some b64 of a secret called myapp-serviceaccounts>
  SECRET_MOUNTS: "/secrets=myapp-serviceaccounts"
  CONFIGMAP_PATH_QUALITY: <a path in this repo containing the definition of a configmap called myapp-configmap>
  CONFIGMAP_MOUNTS: "/configs=myapp-configmap"
```

Read more detail about how to mount secrets/configmaps [here](https://github.com/jobtome-labs/ci-templates/pull/47)

## Google Cloud Run Production

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/cloudrun-production.yml'

stages:
  - deploy

variables:
  GOOGLE_KEY_QUALITY: <google json key>
  GOOGLE_KEY_PRODUCTION: <google json key>
  GOOGLE_PROJECT: my-project
  CLUSTER_NAME_QUALITY: "quality"
  CLUSTER_ZONE_QUALITY: "europe-west1-b"
  CLUSTER_NAME_PRODUCTION: "production"
  CLUSTER_ZONE_PRODUCTION: "europe-west1-b"
  NAMESPACE: my-k8s-namespace-where-cloudrun-is
  SERVICE_NAME: awesome-service
  CONNECTIVITY: "external"
  TIMEOUT: "60s"
  CONCURRENCY: "80"
  CPU: "1000m"
  MEMORY: "128M"
  MAX_INSTANCES: "3"
  ENV_QUALITY: "KEY1=value1,KEY2=value2"
  ENV_PRODUCTION: "KEY1=valueProd1,KEY2=valueProd2"
  SECRET_YAML_QUALITY: <some b64 of a secret called myapp-serviceaccounts>
  SECRET_YAML_PRODUCTION: <some b64 of a secret called myapp-serviceaccounts>
  SECRET_MOUNTS: "/secrets=myapp-serviceaccounts"
  CONFIGMAP_PATH_QUALITY: <a path in this repo containing the definition of a configmap called myapp-configmap>
  CONFIGMAP_PATH_PRODUCTION: <a path in this repo containing the definition of a configmap called myapp-configmap>
  CONFIGMAP_MOUNTS: "/configs=myapp-configmap"
```

Read more detail about how to mount secrets/configmaps [here](https://github.com/jobtome-labs/ci-templates/pull/47)

## Google Dataflow

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/dataflow-production.yml'

stages:
  - deploy

variables:
  GOOGLE_PROJECT: my-project

  GOOGLE_KEY_QUALITY: <google json key>
  TEMPLATE_NAME_QUALITY: my-template
  STAGING_LOCATION_QUALITY: gs://bucket
  TEMPORARY_LOCATION_QUALITY: gs://bucket
  TEMPLATE_LOCATION_QUALITY: gs://bucket
  EXTRA_ARGUMENTS_QUALITY: "--args1=value1 --args2=value2"

  GOOGLE_KEY_PRODUCTION: <google json key>
  TEMPLATE_NAME_PRODUCTION: my-template
  STAGING_LOCATION_PRODUCTION: gs://bucket
  TEMPORARY_LOCATION_PRODUCTION: gs://bucket
  TEMPLATE_LOCATION_PRODUCTION: gs://bucket
  EXTRA_ARGUMENTS_PRODUCTION: "--args1=value1 --args2=value2"
```

## Terraform pipeline

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/terraform.yml'

cache:
  paths:
    - "${TF_FOLDER_PATH}/.terraform"

variables:
  TF_FOLDER_PATH: platform

stages:
  - validate
  - test
  - build
  - deploy
```

## Terraform security score

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/test-terraform-security.yml'

stages:
  - test
```

## Bash script execution

It could be useful to have a script executed through a pipeline. This enables code reviews, programmatic execution (of the script, and of checks beforehands), and avoids 'works on my machine' cases. Our most prominent use-case is when we have to work on the terraform state.
```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/shell-job.yml'

stages:
  - lint
  - deploy
```

NOTE:
- the file does not need to be executable, the pipeline will do `chmod +x`
- the script name to be launched (e.g. `test-script.sh`) MUST be passed as variable with name `SCRIPT_NAME` in the 'manual' deploy phase (see picture). If the script needs it, a variable `ARGUMENTS` can also be passed. The receiving script must know how to use them!

![Example of gitlab](gitlab-manual.jpg)

## Notify sentry of release

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/jobtome-labs/ci-templates/<REF>/sentry.yml'

stages:
  - notify

variables:
  SENTRY_AUTH_TOKEN: my-sentry-user-token
  SENTRY_URL: my-sentry.example.net
  SENTRY_PROJECT: my-sentry-project
  SENTRY_ORG: my-sentry-org
```

This stage uses `getsentry/sentry-cli:1.52.3`, in order to announce a new release [as per the docs](https://docs.sentry.io/workflow/releases/?platform=javascript#using-the-cli).

# General advices

To test stuff in local, try to follow [this guide](https://medium.com/@umutuluer/how-to-test-gitlab-ci-locally-f9e6cef4f054).

In short:

`brew install gitlab-runner`

Before running the following command, go to your project's settings -> CI/CD, select "runners" and get the info (URL and token) specified at "Set up a specific Runner manually"

`gitlab-runner register` -> follow the wizard, select docker as your preferred executor type. When asked for a default docker image, pick a random one because it doesn't matter which one.

Now you can go in a project folder on your laptop, and run

`gitlab-runner exec docker JOBNAME`

This command will look for the `.gitlab-ci.yml` file and look for the job with the specified name.

**It is not possible to run a whole stage. _Jobs must be specifed manually_**

_As a consequence, the classic `.gitlab-ci.yml` file that imports from other yml files (the whole point of this repo) will not work_

Notice there is also [this guide](https://medium.com/@campfirecode/debugging-gitlab-ci-pipelines-locally-e2699608f4df) who doesn't register the runner... `¯\_(ツ)_/¯`
