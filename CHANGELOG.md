# Changelog

## [1.0.3](https://github.com/chanzuckerberg/platformics/compare/v1.0.2...v1.0.3) (2025-04-01)


### Bug Fixes

* include overriden template file paths in codegen'd file header. ([#135](https://github.com/chanzuckerberg/platformics/issues/135)) ([a68e58a](https://github.com/chanzuckerberg/platformics/commit/a68e58a5241de9863c1f9017c0de826bb377f521))

## [1.0.2](https://github.com/chanzuckerberg/platformics/compare/v1.0.1...v1.0.2) (2025-04-01)


### Bug Fixes

* Document code better and add relay fields back. ([#134](https://github.com/chanzuckerberg/platformics/issues/134)) ([3fd9e52](https://github.com/chanzuckerberg/platformics/commit/3fd9e521b6c6d8c37ecd116fbcc8e999e141da7b))
* Handle ValueError exceptions that come from the Strawberry Relay implementation ([#132](https://github.com/chanzuckerberg/platformics/issues/132)) ([97b48cd](https://github.com/chanzuckerberg/platformics/commit/97b48cd5f6a1dd148585507759006718a2329f7a))

## [1.0.1](https://github.com/chanzuckerberg/platformics/compare/v1.0.0...v1.0.1) (2025-03-27)


### Bug Fixes

* Update release action config. ([#130](https://github.com/chanzuckerberg/platformics/issues/130)) ([dac33c1](https://github.com/chanzuckerberg/platformics/commit/dac33c1f2b31c78bf76b7e9acdd2a41d2bd4b0d4))

## [1.0.0](https://github.com/chanzuckerberg/platformics/compare/v0.4.1...v1.0.0) (2025-03-26)


### ⚠ BREAKING CHANGES

* Support classes that don't descend from Entity ([#127](https://github.com/chanzuckerberg/platformics/issues/127))
* remove file handling ([#124](https://github.com/chanzuckerberg/platformics/issues/124))

### Features

* Support classes that don't descend from Entity ([#127](https://github.com/chanzuckerberg/platformics/issues/127)) ([e1b7bb2](https://github.com/chanzuckerberg/platformics/commit/e1b7bb2aae7f9f7b22aa5edd7e6672488714b794))
* Make authorization code pluggable ([#102](https://github.com/chanzuckerberg/platformics/issues/102)) ([09218c4](https://github.com/chanzuckerberg/platformics/commit/09218c460a8c11d813f3ca8e9c22744931453792))
* remove file handling ([#124](https://github.com/chanzuckerberg/platformics/issues/124)) ([ac03bce](https://github.com/chanzuckerberg/platformics/commit/ac03bce56648a8e00c4c82bc2d4d9ba921b7b44e))


### Bug Fixes

* faker generation ([#120](https://github.com/chanzuckerberg/platformics/issues/120)) ([189c558](https://github.com/chanzuckerberg/platformics/commit/189c5586094d6a3c6f111c3be8268b6e7ededc52))

## [0.4.1](https://github.com/chanzuckerberg/platformics/compare/v0.4.0...v0.4.1) (2024-10-21)


### Bug Fixes

* Don't create migration if there are no schema changes ([#118](https://github.com/chanzuckerberg/platformics/issues/118)) ([979518b](https://github.com/chanzuckerberg/platformics/commit/979518b76f79894ee1d798b966d0279f04d292ab))

## [0.4.0](https://github.com/chanzuckerberg/platformics/compare/v0.3.0...v0.4.0) (2024-10-18)


### Features

* add default none to pydantic validators ([#116](https://github.com/chanzuckerberg/platformics/issues/116)) ([1af830c](https://github.com/chanzuckerberg/platformics/commit/1af830ce8d760b33cce270b6b7349536e9707670))

## [0.3.0](https://github.com/chanzuckerberg/platformics/compare/v0.2.0...v0.3.0) (2024-10-10)


### Features

* add list 1d string column ([#111](https://github.com/chanzuckerberg/platformics/issues/111)) ([8b9b9a5](https://github.com/chanzuckerberg/platformics/commit/8b9b9a569fe9d9abfea631f5bedc3e24d7cdc840))
* revert meta import ([#114](https://github.com/chanzuckerberg/platformics/issues/114)) ([d56a097](https://github.com/chanzuckerberg/platformics/commit/d56a0973bc70daf6612877f087c6ff495e462ef8))

## [0.2.0](https://github.com/chanzuckerberg/platformics/compare/v0.1.1...v0.2.0) (2024-10-07)


### Features

* allow ability to add global dependencies ([#110](https://github.com/chanzuckerberg/platformics/issues/110)) ([90bb9b6](https://github.com/chanzuckerberg/platformics/commit/90bb9b6611867c31839fa5b0766739ea65767526))


### Bug Fixes

* update import in env.py ([#107](https://github.com/chanzuckerberg/platformics/issues/107)) ([791d439](https://github.com/chanzuckerberg/platformics/commit/791d43942f756bbb70f8358206b9990f50a0c6da))

## [0.1.1](https://github.com/chanzuckerberg/platformics/compare/v0.1.0...v0.1.1) (2024-08-01)


### Bug Fixes

* use shared infra github token for release please ([#92](https://github.com/chanzuckerberg/platformics/issues/92)) ([78e7da7](https://github.com/chanzuckerberg/platformics/commit/78e7da7499c0879d1edebbd2535c0ea3fac6a2e2))

## 0.1.0 (2024-07-31)


### Features

* (test release action) use git as versioning ([#90](https://github.com/chanzuckerberg/platformics/issues/90)) ([6da3e21](https://github.com/chanzuckerberg/platformics/commit/6da3e21f534c6dee857ddb5f455de50d4fe99227))
* support LinkML field names with spaces. ([#75](https://github.com/chanzuckerberg/platformics/issues/75)) ([f7636ed](https://github.com/chanzuckerberg/platformics/commit/f7636eddd07642adc248439dd0811cffa0ba6628))


### Bug Fixes

* specify when build and test should run ([#91](https://github.com/chanzuckerberg/platformics/issues/91)) ([8f09e57](https://github.com/chanzuckerberg/platformics/commit/8f09e57ccb9c4fe3f629175488e962433dc998ed))
