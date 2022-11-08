BOT_CFLAGS := -Wall -Wextra -Wpedantic -Wno-char-subscripts --std=c17 -pthread
BOT_LIBS := -pthread -lcrypto

SRCDIR := src
OUTDIR := out
DISTDIR := ../dist
CHECKDIR := ../checkers
EXPLOITDIR := ../exploits

BINDIR := $(OUTDIR)/bin
OBJDIR := $(OUTDIR)/obj

SRCDIR_BOT := $(SRCDIR)/bot
BINDIR_BOT := $(BINDIR)/bot
OBJDIR_BOT := $(OBJDIR)/bot
DISTDIR_BOT := $(DISTDIR)/bot

SRCDIR_DOCKER := $(SRCDIR)/docker

SRCDIR_COMMON := $(SRCDIR)/common

SRCDIR_DIST := $(SRCDIR)/dist

TARGET_BOT := bot
SRCS_BOT := $(notdir $(wildcard $(SRCDIR_BOT)/*.c))
OBJS_BOT := $(patsubst %.c,$(OBJDIR_BOT)/%.o,$(SRCS_BOT))
DEPS_BOT := $(patsubst %.o,%.d,$(OBJS_BOT))
DIST_TARGETS_BOT := \
	$(DISTDIR_BOT)/$(TARGET_BOT) \
	$(DISTDIR_BOT)/Dockerfile

SRCDIR_SERVER := $(SRCDIR)/server
DISTDIR_SERVER := $(DISTDIR)/server

SRCS_SERVER := $(notdir \
	$(wildcard $(SRCDIR_SERVER)/*.py) \
	$(wildcard $(SRCDIR_SERVER)/*.txt))
DIST_TARGETS_SERVER := \
	$(patsubst %,$(DISTDIR_SERVER)/%,$(SRCS_SERVER)) \
	$(DISTDIR_SERVER)/Dockerfile

DISTDIR_CLIENT := $(DISTDIR)/client

TARGET_DIRS_COMMON_PROTOCOL := \
	$(DISTDIR_SERVER) \
	$(DISTDIR_CLIENT) \
	$(wildcard $(CHECKDIR)/checker*) \
	$(EXPLOITDIR)
TARGET_DIRS_COMMON_CLIENT := \
	$(DISTDIR_CLIENT) \
	$(wildcard $(CHECKDIR)/checker*) \
	$(EXPLOITDIR)
TARGET_DIRS_COMMON_BOT_CLIENT := \
	$(wildcard $(CHECKDIR)/checker*) \
	$(EXPLOITDIR)
TARGET_DIRS_COMMON_CHECKER_RAND := \
	$(wildcard $(CHECKDIR)/checker*)
TARGET_DIRS_COMMON_CHECKER_UTIL := \
	$(wildcard $(CHECKDIR)/checker*)
DIST_TARGETS_COMMON := \
	$(addsuffix /protocol.py,$(TARGET_DIRS_COMMON_PROTOCOL)) \
	$(addsuffix /client.py,$(TARGET_DIRS_COMMON_CLIENT)) \
	$(addsuffix /bot_client.py,$(TARGET_DIRS_COMMON_BOT_CLIENT)) \
	$(addsuffix /checker_rand.py,$(TARGET_DIRS_COMMON_CHECKER_RAND)) \
	$(addsuffix /checker_util.py,$(TARGET_DIRS_COMMON_CHECKER_UTIL))

DIST_TARGETS_CP := \
	$(addprefix $(DISTDIR)/,$(notdir $(wildcard $(SRCDIR_DIST)/*)))

DIST_TARGETS := \
	$(DIST_TARGETS_BOT) \
	$(DIST_TARGETS_SERVER) \
	$(DIST_TARGETS_COMMON) \
	$(DIST_TARGETS_CP) \
	$(DISTDIR)/docker-compose.yml

.SUFFIXES:
.DEFAULT_GOAL := dist

$(BINDIR_BOT) $(OBJDIR_BOT) $(sort $(dir $(DIST_TARGETS))):
	@mkdir -p $@

-include $(DEPS_BOT)

$(OBJDIR_BOT)/%.o: $(SRCDIR_BOT)/%.c | $(OBJDIR_BOT)
	@echo 'CC  $@'
	@$(CC) $(BOT_CFLAGS) -MMD -c -o $@ $<

$(BINDIR_BOT)/$(TARGET_BOT): $(OBJS_BOT) | $(BINDIR_BOT)
	@echo 'LNK $@'
	@$(CC) -o $@ $^ $(BOT_LIBS)

define cp-rule
$(1): $(2) | $(dir $(1))
	@echo 'CP  $$@'
	@cp $$< $$@
endef

$(eval $(call cp-rule,$(DISTDIR_BOT)/%,$(BINDIR_BOT)/%))
$(eval $(call cp-rule,$(DISTDIR_SERVER)/%,$(SRCDIR_SERVER)/%))
$(eval $(call cp-rule,$(DISTDIR)/%/Dockerfile,$(SRCDIR_DOCKER)/Dockerfile.%))
$(eval $(call cp-rule,$(DISTDIR)/docker-compose.yml,$(SRCDIR_DOCKER)/docker-compose.yml))

$(foreach dst,$(DIST_TARGETS_COMMON),\
	$(eval $(call cp-rule,$(dst),$(SRCDIR_COMMON)/$(notdir $(dst)))))

$(foreach dst,$(DIST_TARGETS_CP),\
	$(eval $(call cp-rule,$(dst),$(SRCDIR_DIST)/$(notdir $(dst)))))

dist: $(DIST_TARGETS)
.PHONY: dist

build: $(BINDIR_BOT)/$(TARGET_BOT)
.PHONY: build

clean:
	@echo 'RM  $(OUTDIR)'
	@rm -rf $(OUTDIR)
.PHONY: clean

distclean: clean
	@echo 'RM  COMMON'
	@rm -rf $(DIST_TARGETS_COMMON)
	@echo 'RM  $(DISTDIR)'
	@rm -rf $(DISTDIR)
.PHONY: distclean

format:
	@echo 'FMT $(SRCDIR_BOT)'
	@clang-format -i $(wildcard $(SRCDIR_BOT)/*.c) $(wildcard $(SRCDIR_BOT)/*.h)
	@echo 'FMT ..'
	@python3 -m autopep8 --in-place --recursive ..
.PHONY: format
