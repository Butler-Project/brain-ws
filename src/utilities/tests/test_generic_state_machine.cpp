#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include "utilities/state_machine/generic_state_machine.h"

namespace {

struct Idle {};
struct Checking {};
struct Done {};

struct Start {};
struct Finish {};
struct Unknown {};

struct Context {
  ::testing::MockFunction<void()> on_start;
};

struct OnStartAction {
  void operator()(Context& context, const Idle&, const Start&, const Checking&) const {
    context.on_start.Call();
  }
};

using States = std::variant<Idle, Checking, Done>;
using Events = std::variant<Start, Finish, Unknown>;
using Table = std::tuple<
    utilities::state_machine::Transition<Idle, Start, Checking, OnStartAction>,
    utilities::state_machine::Transition<Checking, Finish, Done>>;

static_assert(
    utilities::state_machine::is_valid_transition_table_v<States, Events, Table>,
    "Transition table must satisfy FSM compile-time contracts");

using StateMachine =
    utilities::state_machine::StateMachine<States, Events, Table, Context>;

TEST(GenericStateMachine, ExecutesActionAndTransitions) {
  Context context{};
  StateMachine machine{Idle{}, context};

  EXPECT_CALL(context.on_start, Call()).Times(1);
  auto result = machine.dispatch(Start{});

  EXPECT_TRUE(result.transitioned);
  EXPECT_EQ(result.error, utilities::state_machine::Error::none);
  EXPECT_TRUE(std::holds_alternative<Checking>(machine.state()));
}

TEST(GenericStateMachine, ReportsNoTransition) {
  Context context{};
  StateMachine machine{Idle{}, context};

  auto result = machine.dispatch(Unknown{});

  EXPECT_FALSE(result.transitioned);
  EXPECT_EQ(result.error, utilities::state_machine::Error::no_transition);
  EXPECT_TRUE(std::holds_alternative<Idle>(machine.state()));
}

TEST(GenericStateMachine, TransitionsAcrossMultipleSteps) {
  Context context{};
  StateMachine machine{Idle{}, context};

  auto first = machine.dispatch(Start{});
  auto second = machine.dispatch(Finish{});

  EXPECT_TRUE(first.transitioned);
  EXPECT_TRUE(second.transitioned);
  EXPECT_TRUE(std::holds_alternative<Done>(machine.state()));
}

}  // namespace
