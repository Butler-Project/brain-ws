#pragma once

#include <tuple>
#include <type_traits>
#include <utility>
#include <variant>

namespace utilities::state_machine {

struct NoAction {
  template <typename... Args>
  constexpr void operator()(Args&&...) const noexcept {}
};

enum class Error: std::uint8_t {
  none,
  no_transition
};

template <typename StateVariant>
struct TransitionResult {
  bool transitioned{false};
  Error error{Error::no_transition};
  StateVariant from;
  StateVariant to;
};

template <typename From, typename Event, typename To, typename Action = NoAction>
struct Transition {};

namespace detail {

struct NoContext {};

template <typename T>
struct is_tuple : std::false_type {};

template <typename... T>
struct is_tuple<std::tuple<T...>> : std::true_type {};

template <typename T>
inline constexpr bool is_tuple_v = is_tuple<T>::value;

template <typename T>
struct is_variant : std::false_type {};

template <typename... T>
struct is_variant<std::variant<T...>> : std::true_type {};

template <typename T>
inline constexpr bool is_variant_v = is_variant<T>::value;

template <typename T>
struct is_transition : std::false_type {};

template <typename From, typename Event, typename To, typename Action>
struct is_transition<Transition<From, Event, To, Action>> : std::true_type {};

template <typename T>
inline constexpr bool is_transition_v = is_transition<T>::value;

template <typename T, typename Variant>
struct variant_contains;

template <typename T, typename... Ts>
struct variant_contains<T, std::variant<Ts...>> : std::bool_constant<(std::is_same_v<T, Ts> || ...)> {};

template <typename T, typename Variant>
inline constexpr bool variant_contains_v = variant_contains<T, Variant>::value;

template <typename TransitionT>
struct transition_traits;

template <typename From, typename Event, typename To, typename Action>
struct transition_traits<Transition<From, Event, To, Action>> {
  using from = From;
  using event = Event;
  using to = To;
  using action = Action;
};

template <typename Tuple>
struct all_transition_entries;

template <typename... Ts>
struct all_transition_entries<std::tuple<Ts...>> : std::bool_constant<(is_transition_v<Ts> && ...)> {};

template <typename A, typename B>
inline constexpr bool same_transition_key_v =
    std::is_same_v<typename transition_traits<A>::from, typename transition_traits<B>::from> &&
    std::is_same_v<typename transition_traits<A>::event, typename transition_traits<B>::event>;

template <typename... Ts>
struct has_duplicate_pairs;

template <>
struct has_duplicate_pairs<> : std::false_type {};

template <typename T>
struct has_duplicate_pairs<T> : std::false_type {};

template <typename T, typename... Rest>
struct has_duplicate_pairs<T, Rest...>
    : std::bool_constant<((same_transition_key_v<T, Rest>) || ...) ||
                         has_duplicate_pairs<Rest...>::value> {};

template <typename StateVariant, typename EventVariant, typename Tuple, bool AllTransitions>
struct transition_table_validator_impl;

template <typename StateVariant, typename EventVariant, typename... Ts>
struct transition_table_validator_impl<StateVariant, EventVariant, std::tuple<Ts...>, true> {
  static constexpr bool states_in_variant =
      ((variant_contains_v<typename transition_traits<Ts>::from, StateVariant> &&
        variant_contains_v<typename transition_traits<Ts>::to, StateVariant>) &&
       ...);
  static constexpr bool events_in_variant =
      (variant_contains_v<typename transition_traits<Ts>::event, EventVariant> && ...);
  static constexpr bool unique_pairs = !has_duplicate_pairs<Ts...>::value;
};

template <typename StateVariant, typename EventVariant, typename... Ts>
struct transition_table_validator_impl<StateVariant, EventVariant, std::tuple<Ts...>, false> {
  static constexpr bool states_in_variant = false;
  static constexpr bool events_in_variant = false;
  static constexpr bool unique_pairs = false;
};

template <typename StateVariant, typename EventVariant, typename Tuple>
struct transition_table_validator {
  static constexpr bool all_transitions = all_transition_entries<Tuple>::value;
  using impl = transition_table_validator_impl<StateVariant, EventVariant, Tuple, all_transitions>;
  static constexpr bool states_in_variant = impl::states_in_variant;
  static constexpr bool events_in_variant = impl::events_in_variant;
  static constexpr bool unique_pairs = impl::unique_pairs;
  static constexpr bool value =
      all_transitions && states_in_variant && events_in_variant && unique_pairs;
};

template <typename T>
T& default_context() {
  static T instance{};
  return instance;
}

template <typename Action, typename Context, typename From, typename Event, typename To>
void invoke_action(Context& context, const From& from, const Event& event, const To& to) {
  Action action{};
  if constexpr (std::is_invocable_v<Action, Context&, const From&, const Event&, const To&>) {
    action(context, from, event, to);
  } else if constexpr (std::is_invocable_v<Action, const From&, const Event&, const To&>) {
    action(from, event, to);
  } else if constexpr (std::is_invocable_v<Action, Context&, const From&, const Event&>) {
    action(context, from, event);
  } else if constexpr (std::is_invocable_v<Action, const From&, const Event&>) {
    action(from, event);
  } else if constexpr (std::is_invocable_v<Action, Context&>) {
    action(context);
  } else if constexpr (std::is_invocable_v<Action>) {
    action();
  } else {
    static_assert(std::is_invocable_v<Action>, "Action has no supported call signature");
  }
}

}  // namespace detail

template <typename StateVariant, typename EventVariant, typename TransitionTable>
inline constexpr bool is_valid_transition_table_v =
    detail::transition_table_validator<StateVariant, EventVariant, TransitionTable>::value;

template <typename StateVariant,
          typename EventVariant,
          typename TransitionTable,
          typename Context = detail::NoContext>
class StateMachine {
  static_assert(detail::is_variant_v<StateVariant>, "StateVariant must be std::variant");
  static_assert(detail::is_variant_v<EventVariant>, "EventVariant must be std::variant");
  static_assert(detail::is_tuple_v<TransitionTable>, "TransitionTable must be std::tuple");
  static_assert(detail::transition_table_validator<StateVariant, EventVariant, TransitionTable>::all_transitions,
                "TransitionTable must contain Transition<...> entries only");
  static_assert(detail::transition_table_validator<StateVariant, EventVariant, TransitionTable>::states_in_variant,
                "TransitionTable uses states not present in StateVariant");
  static_assert(detail::transition_table_validator<StateVariant, EventVariant, TransitionTable>::events_in_variant,
                "TransitionTable uses events not present in EventVariant");
  static_assert(detail::transition_table_validator<StateVariant, EventVariant, TransitionTable>::unique_pairs,
                "TransitionTable has duplicate (state,event) pairs");

 public:
  using state_variant = StateVariant;
  using event_variant = EventVariant;
  using table_type = TransitionTable;
  using context_type = Context;
  using result_type = TransitionResult<state_variant>;

  explicit StateMachine(state_variant initial)
      : state_(std::move(initial)),
        context_(detail::default_context<context_type>()) {}

  StateMachine(state_variant initial, context_type& context)
      : state_(std::move(initial)),
        context_(context) {}

  const state_variant& state() const noexcept { return state_; }
  context_type& context() noexcept { return context_; }
  const context_type& context() const noexcept { return context_; }

  template <typename Event>
  result_type dispatch(Event&& event) {
    using event_type = std::decay_t<Event>;
    static_assert(detail::variant_contains_v<event_type, event_variant>,
                  "Event must be one of the EventVariant alternatives");
    return dispatch(event_variant{std::forward<Event>(event)});
  }

  result_type dispatch(event_variant event) {
    return std::visit(
        [&](auto&& current_state) -> result_type {
          return std::visit(
              [&](auto&& current_event) -> result_type {
                return dispatch_impl(current_state, current_event);
              },
              event);
        },
        state_);
  }

 private:
  template <typename State, typename Event>
  result_type dispatch_impl(const State& current_state, const Event& current_event) {
    result_type result{false, Error::no_transition, state_, state_};

    bool matched = false;
    std::apply(
        [&](auto... transitions) {
          (try_transition<State, Event, std::decay_t<decltype(transitions)>>(
               matched, result, current_state, current_event),
           ...);
        },
        table_type{});

    if (!matched) {
      result.transitioned = false;
      result.error = Error::no_transition;
    }

    return result;
  }

  template <typename State, typename Event, typename TransitionT>
  void try_transition(bool& matched,
                      result_type& result,
                      const State& current_state,
                      const Event& current_event) {
    if (matched) {
      return;
    }

    using traits = detail::transition_traits<TransitionT>;
    if constexpr (std::is_same_v<State, typename traits::from> &&
                  std::is_same_v<Event, typename traits::event>) {
      matched = true;
      result.transitioned = true;
      result.error = Error::none;

      typename traits::to next_state{};
      detail::invoke_action<typename traits::action>(
          context_, current_state, current_event, next_state);

      state_ = next_state;
      result.to = state_;
    }
  }

  state_variant state_;
  context_type& context_;
};

}  // namespace utilities::state_machine
